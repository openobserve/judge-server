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

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EvaluateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    scorer_name: str = Field(..., min_length=1)
    input: str | None = None
    output: str = Field(..., min_length=1)
    expected: str | None = None
    metadata: dict[str, Any] | None = None


class EvaluateResponseMetadata(BaseModel):
    reason: str
    model: str
    elapsed_ms: int


class EvaluateResponse(BaseModel):
    value: float | str | bool
    metadata: EvaluateResponseMetadata


class HealthResponse(BaseModel):
    status: str
    version: str
    backend: str
    model: str


class VersionResponse(BaseModel):
    version: str
    api_version: str
