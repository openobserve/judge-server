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

from dataclasses import dataclass
from typing import Literal

from . import prompts
from .parser import (
    ParsedScore,
    ScoreParseError,
    parse_boolean,
    parse_categorical,
    parse_numeric,
)

ScorerKind = Literal["numeric", "categorical", "boolean"]


@dataclass(frozen=True)
class Scorer:
    name: str
    kind: ScorerKind
    prompt_template: str
    requires_input: bool
    categorical_labels: tuple[str, ...] = ()

    def render(self, *, input_text: str | None, output_text: str) -> str:
        if self.requires_input and not input_text:
            raise ValueError(
                f"scorer {self.name!r} requires a non-empty 'input' field"
            )
        return (
            self.prompt_template
            .replace("{{input}}", input_text or "")
            .replace("{{output}}", output_text)
        )

    def parse(self, llm_text: str) -> ParsedScore:
        if self.kind == "numeric":
            return parse_numeric(llm_text)
        if self.kind == "categorical":
            return parse_categorical(llm_text, labels=self.categorical_labels)
        if self.kind == "boolean":
            return parse_boolean(llm_text)
        raise ScoreParseError(f"unknown scorer kind: {self.kind!r}")


_ALL: tuple[Scorer, ...] = (
    Scorer(
        name="hallucination",
        kind="numeric",
        prompt_template=prompts.HALLUCINATION,
        requires_input=True,
    ),
    Scorer(
        name="answer_relevance",
        kind="numeric",
        prompt_template=prompts.ANSWER_RELEVANCE,
        requires_input=True,
    ),
    Scorer(
        name="coherence",
        kind="numeric",
        prompt_template=prompts.COHERENCE,
        requires_input=False,
    ),
    Scorer(
        name="helpfulness",
        kind="numeric",
        prompt_template=prompts.HELPFULNESS,
        requires_input=True,
    ),
    Scorer(
        name="instruction_following",
        kind="categorical",
        prompt_template=prompts.INSTRUCTION_FOLLOWING,
        requires_input=True,
        categorical_labels=("low", "medium", "high"),
    ),
    Scorer(
        name="toxicity",
        kind="categorical",
        prompt_template=prompts.TOXICITY,
        requires_input=False,
        categorical_labels=("low", "medium", "high"),
    ),
    Scorer(
        name="bias",
        kind="boolean",
        prompt_template=prompts.BIAS,
        requires_input=False,
    ),
    Scorer(
        name="output_format",
        kind="boolean",
        prompt_template=prompts.OUTPUT_FORMAT,
        requires_input=True,
    ),
)

REGISTRY: dict[str, Scorer] = {s.name: s for s in _ALL}


def get_scorer(name: str) -> Scorer | None:
    return REGISTRY.get(name)


def scorer_names() -> tuple[str, ...]:
    return tuple(REGISTRY.keys())
