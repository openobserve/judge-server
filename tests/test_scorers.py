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

from judge_server.scorers import REGISTRY, scorer_names


def test_all_eight_scorers_registered() -> None:
    expected = {
        "hallucination",
        "answer_relevance",
        "coherence",
        "helpfulness",
        "instruction_following",
        "toxicity",
        "bias",
        "output_format",
    }
    assert set(scorer_names()) == expected
    assert len(REGISTRY) == 8


def test_render_substitutes_placeholders() -> None:
    scorer = REGISTRY["hallucination"]
    rendered = scorer.render(input_text="QUESTION_HERE", output_text="ANSWER_HERE")
    assert "QUESTION_HERE" in rendered
    assert "ANSWER_HERE" in rendered
    assert "{{input}}" not in rendered
    assert "{{output}}" not in rendered


def test_render_pattern_b_does_not_need_input() -> None:
    scorer = REGISTRY["coherence"]
    rendered = scorer.render(input_text=None, output_text="OUT")
    assert "OUT" in rendered
    assert "{{output}}" not in rendered


def test_render_pattern_a_requires_input() -> None:
    scorer = REGISTRY["hallucination"]
    with pytest.raises(ValueError):
        scorer.render(input_text=None, output_text="OUT")
    with pytest.raises(ValueError):
        scorer.render(input_text="", output_text="OUT")


def test_requires_input_assignment_matches_doc_03() -> None:
    # Pattern A / B assignment per the OpenObserve Remote Scorer spec.
    pattern_a = {
        "hallucination",
        "answer_relevance",
        "helpfulness",
        "instruction_following",
        "output_format",
    }
    pattern_b = {"coherence", "toxicity", "bias"}
    for name in pattern_a:
        assert REGISTRY[name].requires_input is True, name
    for name in pattern_b:
        assert REGISTRY[name].requires_input is False, name


def test_kinds_match_doc_03() -> None:
    expected = {
        "hallucination": "numeric",
        "answer_relevance": "numeric",
        "coherence": "numeric",
        "helpfulness": "numeric",
        "instruction_following": "categorical",
        "toxicity": "categorical",
        "bias": "boolean",
        "output_format": "boolean",
    }
    for name, kind in expected.items():
        assert REGISTRY[name].kind == kind, name
