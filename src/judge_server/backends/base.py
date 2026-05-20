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

from abc import ABC, abstractmethod
from dataclasses import dataclass


class LLMTimeout(Exception):
    """LLM backend timed out (→ HTTP 504)."""


class LLMTransportError(Exception):
    """LLM backend could not be reached or returned a transport-level error (→ HTTP 502)."""


@dataclass(frozen=True)
class LLMResult:
    text: str
    model: str


class LLMBackend(ABC):
    @abstractmethod
    async def complete(self, prompt: str) -> LLMResult:
        """Run a single completion. Implementations must translate
        timeout / connection errors into LLMTimeout / LLMTransportError."""
