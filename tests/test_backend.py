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

import pytest

from judge_server.backends import build_backend, build_model_string
from judge_server.config import ConfigError, Settings


@pytest.mark.parametrize(
    ("provider", "model", "expected"),
    [
        ("openai", "gpt-5-mini", "gpt-5-mini"),
        ("openai_compatible", "llama-3.1-70b-instruct", "openai/llama-3.1-70b-instruct"),
        ("anthropic", "claude-3-5-sonnet-20241022", "anthropic/claude-3-5-sonnet-20241022"),
        ("gemini", "gemini-1.5-pro", "gemini/gemini-1.5-pro"),
        ("vertex_ai", "gemini-1.5-pro", "vertex_ai/gemini-1.5-pro"),
        ("bedrock", "anthropic.claude-3-sonnet-20240229-v1:0", "bedrock/anthropic.claude-3-sonnet-20240229-v1:0"),
        ("azure", "my-deployment", "azure/my-deployment"),
        ("ollama", "llama3", "ollama/llama3"),
        ("groq", "llama-3.1-70b-versatile", "groq/llama-3.1-70b-versatile"),
        ("deepseek", "deepseek-chat", "deepseek/deepseek-chat"),
    ],
)
def test_build_model_string(provider: str, model: str, expected: str) -> None:
    assert build_model_string(provider, model) == expected


def _settings(**overrides) -> Settings:
    base = {
        "auth_token": "t",
        "backend": "openai",
        "backend_api_key": "sk-test",
        "backend_model": "gpt-5-mini",
        "backend_url": None,
        "backend_timeout_seconds": 10.0,
        "host": "127.0.0.1",
        "port": 8000,
    }
    base.update(overrides)
    return Settings(**base)


def test_build_backend_routes_anthropic() -> None:
    backend = build_backend(
        _settings(backend="anthropic", backend_model="claude-3-5-sonnet-20241022")
    )
    assert backend._model_string == "anthropic/claude-3-5-sonnet-20241022"


def test_build_backend_passes_api_base_for_compatible() -> None:
    backend = build_backend(
        _settings(
            backend="openai_compatible",
            backend_model="llama-3.1-70b-instruct",
            backend_url="http://internal-llm:8000/v1",
        )
    )
    assert backend._model_string == "openai/llama-3.1-70b-instruct"
    assert backend._api_base == "http://internal-llm:8000/v1"


def test_config_accepts_arbitrary_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("O2_JUDGE_AUTH_TOKEN", "t")
    monkeypatch.setenv("O2_JUDGE_PROVIDER", "anthropic")
    monkeypatch.setenv("O2_JUDGE_API_KEY", "k")
    monkeypatch.setenv("O2_JUDGE_MODEL", "claude-3-5-sonnet-20241022")
    settings = Settings.from_env()
    assert settings.backend == "anthropic"


def test_config_lowercases_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("O2_JUDGE_AUTH_TOKEN", "t")
    monkeypatch.setenv("O2_JUDGE_PROVIDER", "Anthropic")
    monkeypatch.setenv("O2_JUDGE_API_KEY", "k")
    monkeypatch.setenv("O2_JUDGE_MODEL", "m")
    settings = Settings.from_env()
    assert settings.backend == "anthropic"


def test_config_rejects_bogus_provider_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("O2_JUDGE_AUTH_TOKEN", "t")
    monkeypatch.setenv("O2_JUDGE_PROVIDER", "has spaces!")
    monkeypatch.setenv("O2_JUDGE_API_KEY", "k")
    monkeypatch.setenv("O2_JUDGE_MODEL", "m")
    with pytest.raises(ConfigError):
        Settings.from_env()


def test_config_openai_compatible_requires_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("O2_JUDGE_AUTH_TOKEN", "t")
    monkeypatch.setenv("O2_JUDGE_PROVIDER", "openai_compatible")
    monkeypatch.setenv("O2_JUDGE_API_KEY", "k")
    monkeypatch.setenv("O2_JUDGE_MODEL", "m")
    monkeypatch.delenv("O2_JUDGE_URL", raising=False)
    with pytest.raises(ConfigError, match="O2_JUDGE_URL"):
        Settings.from_env()
