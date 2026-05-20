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

import os
import re
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """Raised on missing or invalid environment configuration at startup."""


# LiteLLM provider names are lowercase letters, digits, and underscores
# (e.g. `openai`, `anthropic`, `vertex_ai`, `together_ai`, `bedrock`).
_PROVIDER_RE = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True)
class Settings:
    auth_token: str
    backend: str
    backend_api_key: str
    backend_model: str
    backend_url: str | None
    backend_timeout_seconds: float
    host: str
    port: int

    @classmethod
    def from_env(cls) -> "Settings":
        auth_token = _required("O2_JUDGE_AUTH_TOKEN")

        backend = _required("O2_JUDGE_PROVIDER").lower()
        if not _PROVIDER_RE.match(backend):
            raise ConfigError(
                f"O2_JUDGE_PROVIDER must be a LiteLLM provider name "
                f"(lowercase, digits, underscores), got {backend!r}"
            )

        backend_api_key = _required("O2_JUDGE_API_KEY")
        backend_model = _required("O2_JUDGE_MODEL")

        backend_url: str | None = os.environ.get("O2_JUDGE_URL") or None
        if backend == "openai_compatible" and not backend_url:
            raise ConfigError(
                "O2_JUDGE_URL is required when O2_JUDGE_PROVIDER=openai_compatible"
            )

        timeout = _float_env("O2_JUDGE_TIMEOUT_SECONDS", 60.0)
        if timeout <= 0:
            raise ConfigError("O2_JUDGE_TIMEOUT_SECONDS must be > 0")

        host = os.environ.get("O2_JUDGE_HOST", "0.0.0.0")
        port = _int_env("O2_JUDGE_PORT", 8000)

        return cls(
            auth_token=auth_token,
            backend=backend,
            backend_api_key=backend_api_key,
            backend_model=backend_model,
            backend_url=backend_url,
            backend_timeout_seconds=timeout,
            host=host,
            port=port,
        )


def _required(key: str) -> str:
    value = os.environ.get(key, "").strip()
    if not value:
        raise ConfigError(f"{key} is required")
    return value


def _int_env(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{key} must be an integer, got {raw!r}") from exc


def _float_env(key: str, default: float) -> float:
    raw = os.environ.get(key)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{key} must be a number, got {raw!r}") from exc
