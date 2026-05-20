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
import time

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from . import API_VERSION, __version__
from .auth import make_auth_dependency
from .backends import LLMBackend, LLMTimeout, LLMTransportError, build_backend
from .config import Settings
from .models import (
    EvaluateRequest,
    EvaluateResponse,
    EvaluateResponseMetadata,
    HealthResponse,
    VersionResponse,
)
from .scorers import REGISTRY, get_scorer, scorer_names
from .scorers.parser import ScoreParseError

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    *,
    backend: LLMBackend | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env()
    backend = backend or build_backend(settings)
    require_bearer = make_auth_dependency(settings)

    app = FastAPI(
        title="OpenObserve Reference Judge Server",
        version=__version__,
        docs_url=None,
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.backend = backend

    @app.exception_handler(RequestValidationError)
    async def _on_validation_error(_request: Request, exc: RequestValidationError):
        # Our public API contract uses 400 for "missing required fields"
        # (see README §API). Map FastAPI's default 422 to 400.
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Invalid request body", "errors": exc.errors()},
        )

    @app.get("/version", response_model=VersionResponse)
    async def get_version() -> VersionResponse:
        return VersionResponse(version=__version__, api_version=API_VERSION)

    @app.get(
        "/health",
        response_model=HealthResponse,
        dependencies=[Depends(require_bearer)],
    )
    async def get_health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            version=__version__,
            backend=settings.backend,
            model=settings.backend_model,
        )

    @app.post(
        "/evaluate",
        response_model=EvaluateResponse,
        dependencies=[Depends(require_bearer)],
    )
    async def post_evaluate(body: EvaluateRequest) -> EvaluateResponse:
        scorer = get_scorer(body.scorer_name)
        if scorer is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Unsupported scorer_name {body.scorer_name!r}. "
                    f"Supported: {', '.join(scorer_names())}"
                ),
            )

        if scorer.requires_input and not body.input:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"scorer {scorer.name!r} requires a non-empty 'input'",
            )

        prompt = scorer.render(input_text=body.input, output_text=body.output)

        started = time.perf_counter()
        try:
            llm_result = await app.state.backend.complete(prompt)
        except LLMTimeout as exc:
            logger.warning("LLM timeout for scorer=%s: %s", scorer.name, exc)
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="LLM backend timed out",
            ) from exc
        except LLMTransportError as exc:
            logger.warning("LLM transport error for scorer=%s: %s", scorer.name, exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"LLM backend communication failure: {exc}",
            ) from exc
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        try:
            parsed = scorer.parse(llm_result.text)
        except ScoreParseError as exc:
            logger.warning(
                "Score parse failure for scorer=%s: %s; raw=%s",
                scorer.name,
                exc,
                llm_result.text,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not parse LLM response: {exc}",
            ) from exc

        return EvaluateResponse(
            value=parsed.value,
            metadata=EvaluateResponseMetadata(
                reason=parsed.reasoning,
                model=llm_result.model,
                elapsed_ms=elapsed_ms,
            ),
        )

    logger.info(
        "judge-server initialized: backend=%s model=%s scorers=%d",
        settings.backend,
        settings.backend_model,
        len(REGISTRY),
    )
    return app
