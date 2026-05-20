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

from judge_server.scorers.parser import (
    ScoreParseError,
    parse_boolean,
    parse_categorical,
    parse_numeric,
    parse_reasoning,
)


def test_parse_numeric_extracts_value_and_reasoning() -> None:
    parsed = parse_numeric(
        "<reasoning>Looks fine.</reasoning>\n<score>0.42</score>"
    )
    assert parsed.value == 0.42
    assert parsed.reasoning == "Looks fine."


def test_parse_numeric_clamps_above_one() -> None:
    parsed = parse_numeric("<score>1.5</score>")
    assert parsed.value == 1.0


def test_parse_numeric_clamps_below_zero() -> None:
    parsed = parse_numeric("<score>-0.2</score>")
    assert parsed.value == 0.0


def test_parse_numeric_missing_tag_raises() -> None:
    with pytest.raises(ScoreParseError):
        parse_numeric("no tags here")


def test_parse_categorical_exact_match() -> None:
    parsed = parse_categorical(
        "<category>medium</category>", labels=("low", "medium", "high")
    )
    assert parsed.value == "medium"


def test_parse_categorical_case_and_whitespace_tolerant() -> None:
    parsed = parse_categorical(
        "<category>  HIGH  </category>", labels=("low", "medium", "high")
    )
    assert parsed.value == "high"


def test_parse_categorical_substring_fallback() -> None:
    parsed = parse_categorical(
        "<category>category: low</category>", labels=("low", "medium", "high")
    )
    assert parsed.value == "low"


def test_parse_categorical_unknown_label_raises() -> None:
    with pytest.raises(ScoreParseError):
        parse_categorical(
            "<category>extreme</category>", labels=("low", "medium", "high")
        )


def test_parse_boolean_true_false() -> None:
    assert parse_boolean("<value>true</value>").value is True
    assert parse_boolean("<value>FALSE</value>").value is False


def test_parse_boolean_unknown_raises() -> None:
    with pytest.raises(ScoreParseError):
        parse_boolean("<value>maybe</value>")


def test_parse_reasoning_missing_is_empty_string() -> None:
    assert parse_reasoning("<score>0.5</score>") == ""
