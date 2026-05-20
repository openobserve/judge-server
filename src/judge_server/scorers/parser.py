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

import re
from dataclasses import dataclass


class ScoreParseError(ValueError):
    """Raised when the LLM response cannot be parsed into the expected shape."""


@dataclass(frozen=True)
class ParsedScore:
    value: float | str | bool
    reasoning: str


_TAG_BODY = r"\s*(?P<body>.*?)\s*"


def _extract(tag: str, text: str) -> str | None:
    match = re.search(rf"<{tag}>{_TAG_BODY}</{tag}>", text, re.DOTALL | re.IGNORECASE)
    return match.group("body") if match else None


def parse_reasoning(text: str) -> str:
    return _extract("reasoning", text) or ""


def parse_numeric(text: str, *, lo: float = 0.0, hi: float = 1.0) -> ParsedScore:
    raw = _extract("score", text)
    if raw is None:
        raise ScoreParseError("missing <score> tag")
    match = re.search(r"-?\d+(?:\.\d+)?", raw)
    if match is None:
        raise ScoreParseError(f"could not find a number in <score>: {raw!r}")
    value = float(match.group(0))
    if value < lo:
        value = lo
    elif value > hi:
        value = hi
    return ParsedScore(value=value, reasoning=parse_reasoning(text))


def parse_categorical(text: str, *, labels: tuple[str, ...]) -> ParsedScore:
    raw = _extract("category", text)
    if raw is None:
        raise ScoreParseError("missing <category> tag")
    normalized = raw.strip().lower()
    for label in labels:
        if label.lower() == normalized:
            return ParsedScore(value=label, reasoning=parse_reasoning(text))
    # Fallback: substring match (model may emit "category: low" or "low.")
    for label in labels:
        if re.search(rf"\b{re.escape(label.lower())}\b", normalized):
            return ParsedScore(value=label, reasoning=parse_reasoning(text))
    raise ScoreParseError(
        f"<category> {raw!r} does not match any of {labels!r}"
    )


def parse_boolean(text: str) -> ParsedScore:
    raw = _extract("value", text)
    if raw is None:
        raise ScoreParseError("missing <value> tag")
    normalized = raw.strip().lower()
    if normalized in ("true", "yes"):
        return ParsedScore(value=True, reasoning=parse_reasoning(text))
    if normalized in ("false", "no"):
        return ParsedScore(value=False, reasoning=parse_reasoning(text))
    # Substring fallback
    if re.search(r"\btrue\b", normalized):
        return ParsedScore(value=True, reasoning=parse_reasoning(text))
    if re.search(r"\bfalse\b", normalized):
        return ParsedScore(value=False, reasoning=parse_reasoning(text))
    raise ScoreParseError(f"<value> {raw!r} is not true/false")
