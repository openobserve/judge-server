# Copyright 2026 OpenObserve Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import annotations

import logging
import os

# Use LiteLLM's bundled model cost map instead of fetching it from GitHub
# at import time. We don't use LiteLLM's cost-tracking features, and the
# fetch is a hidden network dependency that fails on air-gapped hosts and
# emits a noisy SSL warning on flaky links. Must be set before
# `import litellm`.
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

# Silence import-time warnings for optional features we don't use
# (botocore-backed Bedrock/SageMaker streaming shape preloads).
logging.getLogger("LiteLLM").setLevel(logging.ERROR)

import litellm  # noqa: E402  (must follow the env/logger setup above)

from ..config import Settings
from .base import LLMBackend, LLMResult, LLMTimeout, LLMTransportError


# Providers that the OpenObserve docs call out explicitly.
# Any other LiteLLM-supported provider name also works — we don't whitelist.
KNOWN_PROVIDERS: tuple[str, ...] = (
    "openai",
    "openai_compatible",
    "anthropic",
    "azure",
    "gemini",
    "vertex_ai",
    "bedrock",
    "cohere",
    "mistral",
    "groq",
    "deepseek",
    "together_ai",
    "fireworks_ai",
    "ollama",
    "replicate",
    "huggingface",
)


def build_model_string(provider: str, model: str) -> str:
    """Build the LiteLLM-format model string from our `(provider, model)` pair.

    `openai` stays bare (LiteLLM treats unprefixed models as OpenAI).
    `openai_compatible` becomes `openai/<model>` so LiteLLM uses the OpenAI
    code path against a custom `api_base`.
    Every other provider is prefixed with `<provider>/`.
    """
    if provider == "openai":
        return model
    if provider == "openai_compatible":
        return f"openai/{model}"
    return f"{provider}/{model}"


class LiteLLMBackend(LLMBackend):
    """Unified LLM backend that delegates to LiteLLM.

    LiteLLM (https://docs.litellm.ai) maps a single OpenAI-shaped API
    onto ~100 providers. Routing is encoded in the `model` string
    (`anthropic/...`, `bedrock/...`, …); per-provider credentials are
    read from standard env vars (`ANTHROPIC_API_KEY`, `AWS_*`,
    `GOOGLE_APPLICATION_CREDENTIALS`, …) — see README §Providers.
    """

    def __init__(
        self,
        *,
        provider: str,
        model: str,
        api_key: str,
        api_base: str | None,
        timeout_seconds: float,
    ) -> None:
        self._provider = provider
        self._model_string = build_model_string(provider, model)
        self._api_key = api_key
        self._api_base = api_base
        self._timeout = timeout_seconds

    async def complete(self, prompt: str) -> LLMResult:
        kwargs: dict = {
            "model": self._model_string,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "timeout": self._timeout,
            "num_retries": 0,
        }
        if self._api_key:
            kwargs["api_key"] = self._api_key
        if self._api_base:
            kwargs["api_base"] = self._api_base

        try:
            response = await litellm.acompletion(**kwargs)
        except litellm.Timeout as exc:
            raise LLMTimeout(str(exc)) from exc
        except (
            litellm.APIConnectionError,
            litellm.ServiceUnavailableError,
        ) as exc:
            raise LLMTransportError(str(exc)) from exc
        except litellm.APIError as exc:
            # Catch-all for upstream errors (auth, rate limit, 5xx, etc.).
            # We surface them as 502 — the spec reserves 500 for our
            # own internal failures.
            raise LLMTransportError(
                f"LLM backend error (status={getattr(exc, 'status_code', '?')}): {exc}"
            ) from exc

        choices = getattr(response, "choices", None) or []
        if not choices:
            raise LLMTransportError("LLM backend returned no choices")
        content = choices[0].message.content or ""
        model_name = getattr(response, "model", None) or self._model_string
        return LLMResult(text=content, model=model_name)


def build_backend(settings: Settings) -> LiteLLMBackend:
    return LiteLLMBackend(
        provider=settings.backend,
        model=settings.backend_model,
        api_key=settings.backend_api_key,
        api_base=settings.backend_url,
        timeout_seconds=settings.backend_timeout_seconds,
    )
