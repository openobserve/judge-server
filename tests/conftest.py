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

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from judge_server.app import create_app
from judge_server.backends.base import LLMBackend, LLMResult
from judge_server.config import Settings


class FakeBackend(LLMBackend):
    def __init__(self, response_text: str = "", model: str = "fake-model") -> None:
        self.response_text = response_text
        self.model = model
        self.calls: list[str] = []
        self._raise: Exception | None = None

    def will_raise(self, exc: Exception) -> None:
        self._raise = exc

    async def complete(self, prompt: str) -> LLMResult:
        self.calls.append(prompt)
        if self._raise is not None:
            raise self._raise
        return LLMResult(text=self.response_text, model=self.model)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        auth_token="test-token",
        backend="openai",
        backend_api_key="sk-test",
        backend_model="gpt-test",
        backend_url=None,
        backend_timeout_seconds=10.0,
        host="127.0.0.1",
        port=8000,
    )


@pytest.fixture
def make_client(settings: Settings) -> Callable[[FakeBackend], TestClient]:
    def _build(backend: FakeBackend) -> TestClient:
        app = create_app(settings, backend=backend)
        return TestClient(app)

    return _build


@pytest.fixture
def client(make_client: Callable[[FakeBackend], TestClient]) -> TestClient:
    return make_client(FakeBackend())


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}
