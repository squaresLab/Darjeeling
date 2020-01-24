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
        return f"building candidate patch [{self.candidate.id}]"


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


@_attr.s(frozen=True, auto_attribs=True, slots=True, str=False)
class TestExecutionStarted(DarjeelingEvent):
    """A test for a given candidate patch has started executing."""
    candidate: _Candidate
    test: _Test

    def __str__(self) -> str:
        return (f"executing test [{self.test.name}]"
                f" for candidate patch [{self.candidate.id}]")


@_attr.s(frozen=True, auto_attribs=True, slots=True, str=False)
class TestExecutionFinished(DarjeelingEvent):
    """A test for a given candidate patch has finished executing."""
    candidate: _Candidate
    test: _Test
    outcome: _TestOutcome

    def __str__(self) -> str:
        status = 'passed' if self.outcome.successful else 'failed'
        return (f"test {status} [{self.test.name}]"
                f" for candidate patch [{self.candidate.id}]")


@_attr.s(frozen=True, auto_attribs=True, slots=True, str=False)
class TestExecutionError(DarjeelingEvent):
    """An unexpected error when executing a test."""
    candidate: _Candidate
    test: _Test
    error: Exception

    def __str__(self) -> str:
        return ("an unexpected error occurred when executing "
                f"test [{self.test.name}] "
                f"for candidate [{self.candidate}]:\n{str(self.error)}")


@_attr.s(frozen=True, auto_attribs=True, slots=True, str=False)
class CandidateEvaluationStarted(DarjeelingEvent):
    """Evaluation of a given candidate patch has started."""
    candidate: _Candidate

    def __str__(self) -> str:
        return f"evaluating candidate patch [{self.candidate.id}]"


@_attr.s(frozen=True, auto_attribs=True, slots=True, str=False)
class CandidateEvaluationFinished(DarjeelingEvent):
    """Evaluation of a given candidate patch has finished."""
    candidate: _Candidate
    outcome: _CandidateOutcome

    def __str__(self) -> str:
        if self.outcome.is_repair:
            return f"found acceptable patch [{self.candidate.id}]"
        else:
            return f"rejected candidate patch [{self.candidate.id}]"


@_attr.s(frozen=True, auto_attribs=True, slots=True, str=False)
class CandidateEvaluationError(DarjeelingEvent):
    """An unexpected error occurred during evaluation of a candidate patch."""
    candidate: _Candidate
    error: Exception

    def __str__(self) -> str:
        return (f"unexpected error during evaluation of candidate patch"
                f" [{self.candidate.id}]: {str(self.error)}")
