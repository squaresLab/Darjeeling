# -*- coding: utf-8 -*-
import attr as _attr

from ..core import (Test as _Test,
                    TestOutcome as _TestOutcome,
                    BuildOutcome as _BuildOutcome)
from ..candidate import Candidate as _Candidate
from ..outcome import CandidateOutcome as _CandidateOutcome


class DarjeelingEvent:
    """Base class used by all events within Darjeeling."""


@_attr.s(frozen=True, auto_attribs=True, slots=True, str=False)
class BuildStarted(DarjeelingEvent):
    """An attempt to build a candidate patch has started."""
    candidate: _Candidate

    def __str__(self) -> str:
        return f"building candidate patch: {self.candidate.id}"


@_attr.s(frozen=True, auto_attribs=True, slots=True, str=False)
class BuildFinished(DarjeelingEvent):
    """An attempt to build a candidate patch has finished."""
    candidate: _Candidate
    outcome: _BuildOutcome

    def __str__(self) -> str:
        if not self.outcome.successful:
            prefix = "failed to build"
        else:
            prefix = "successfully built"

        s = (f"{prefix} candidate patch [{self.candidate.id}]"
             f" after {self.outcome.time_taken:.3f} seconds.")
        return s


@_attr.s(frozen=True, auto_attribs=True, slots=True)
class TestExecutionStarted(DarjeelingEvent):
    """A test for a given candidate patch has started executing."""
    candidate: _Candidate
    test: _Test


@_attr.s(frozen=True, auto_attribs=True, slots=True)
class TestExecutionFinished(DarjeelingEvent):
    """A test for a given candidate patch has finished executing."""
    candidate: _Candidate
    test: _Test
    outcome: _TestOutcome


@_attr.s(frozen=True, auto_attribs=True, slots=True)
class CandidateEvaluationStarted(DarjeelingEvent):
    """Evaluation of a given candidate patch has started."""
    candidate: _Candidate


@_attr.s(frozen=True, auto_attribs=True, slots=True)
class CandidateEvaluationFinished(DarjeelingEvent):
    """Evaluation of a given candidate patch has finished."""
    candidate: _Candidate
    outcome: _CandidateOutcome


@_attr.s(frozen=True, auto_attribs=True, slots=True)
class CandidateEvaluationError(DarjeelingEvent):
    """An unexpected error occurred during evaluation of a candidate patch."""
    candidate: _Candidate
    error: Exception
