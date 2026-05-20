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

from fastapi.testclient import TestClient

from judge_server import API_VERSION, __version__
from judge_server.backends.base import LLMTimeout, LLMTransportError

from .conftest import FakeBackend


def test_version_is_public(client: TestClient) -> None:
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json() == {"version": __version__, "api_version": API_VERSION}


def test_health_requires_auth(client: TestClient) -> None:
    assert client.get("/health").status_code == 401
    assert (
        client.get("/health", headers={"Authorization": "Bearer wrong"}).status_code
        == 401
    )


def test_health_ok(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/health", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
    assert body["backend"] == "openai"
    assert body["model"] == "gpt-test"


def test_evaluate_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/evaluate", json={"scorer_name": "coherence", "output": "hi"}
    )
    assert response.status_code == 401


def test_evaluate_unknown_scorer_returns_400(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/evaluate",
        headers=auth_headers,
        json={"scorer_name": "nope", "output": "hi"},
    )
    assert response.status_code == 400
    assert "Unsupported scorer_name" in response.json()["detail"]


def test_evaluate_missing_input_returns_400(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    # hallucination requires input
    response = client.post(
        "/evaluate",
        headers=auth_headers,
        json={"scorer_name": "hallucination", "output": "hi"},
    )
    assert response.status_code == 400
    assert "requires a non-empty 'input'" in response.json()["detail"]


def test_evaluate_validation_error_maps_to_400(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post("/evaluate", headers=auth_headers, json={})
    assert response.status_code == 400


def test_evaluate_numeric_success(
    make_client: Callable[[FakeBackend], TestClient],
    auth_headers: dict[str, str],
) -> None:
    backend = FakeBackend(
        response_text=(
            "<reasoning>The output stays on topic.</reasoning>"
            "<score>0.83</score>"
        )
    )
    client = make_client(backend)
    response = client.post(
        "/evaluate",
        headers=auth_headers,
        json={"scorer_name": "coherence", "output": "Some coherent output."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["value"] == 0.83
    assert body["metadata"]["reason"] == "The output stays on topic."
    assert body["metadata"]["model"] == "fake-model"
    assert isinstance(body["metadata"]["elapsed_ms"], int)
    assert "Some coherent output." in backend.calls[0]


def test_evaluate_categorical_success(
    make_client: Callable[[FakeBackend], TestClient],
    auth_headers: dict[str, str],
) -> None:
    backend = FakeBackend(
        response_text="<reasoning>Clean output.</reasoning><category>low</category>"
    )
    client = make_client(backend)
    response = client.post(
        "/evaluate",
        headers=auth_headers,
        json={"scorer_name": "toxicity", "output": "Hello world."},
    )
    assert response.status_code == 200
    assert response.json()["value"] == "low"


def test_evaluate_boolean_success(
    make_client: Callable[[FakeBackend], TestClient],
    auth_headers: dict[str, str],
) -> None:
    backend = FakeBackend(
        response_text="<reasoning>No group-identity content.</reasoning><value>false</value>"
    )
    client = make_client(backend)
    response = client.post(
        "/evaluate",
        headers=auth_headers,
        json={"scorer_name": "bias", "output": "A neutral statement."},
    )
    assert response.status_code == 200
    assert response.json()["value"] is False


def test_evaluate_unparseable_returns_500(
    make_client: Callable[[FakeBackend], TestClient],
    auth_headers: dict[str, str],
) -> None:
    backend = FakeBackend(response_text="no tags here, just garbage")
    client = make_client(backend)
    response = client.post(
        "/evaluate",
        headers=auth_headers,
        json={"scorer_name": "coherence", "output": "Some output."},
    )
    assert response.status_code == 500
    assert "Could not parse" in response.json()["detail"]


def test_evaluate_timeout_returns_504(
    make_client: Callable[[FakeBackend], TestClient],
    auth_headers: dict[str, str],
) -> None:
    backend = FakeBackend()
    backend.will_raise(LLMTimeout("upstream timeout"))
    client = make_client(backend)
    response = client.post(
        "/evaluate",
        headers=auth_headers,
        json={"scorer_name": "coherence", "output": "Some output."},
    )
    assert response.status_code == 504


def test_evaluate_transport_error_returns_502(
    make_client: Callable[[FakeBackend], TestClient],
    auth_headers: dict[str, str],
) -> None:
    backend = FakeBackend()
    backend.will_raise(LLMTransportError("connection refused"))
    client = make_client(backend)
    response = client.post(
        "/evaluate",
        headers=auth_headers,
        json={"scorer_name": "coherence", "output": "Some output."},
    )
    assert response.status_code == 502
