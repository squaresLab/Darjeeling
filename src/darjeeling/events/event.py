from __future__ import annotations

import abc
from typing import Any

import attr as _attr

from darjeeling.candidate import Candidate as _Candidate
from darjeeling.core import BuildOutcome as _BuildOutcome
from darjeeling.core import Test as _Test
from darjeeling.core import TestOutcome as _TestOutcome
from darjeeling.outcome import CandidateOutcome as _CandidateOutcome


class DarjeelingEvent:
    """Base class used by all events within Darjeeling."""
    @property  # type: ignore[misc]
    @classmethod
    @abc.abstractmethod
    def NAME(cls) -> str:
        ...

    def to_dict(self) -> dict[str, Any]:
        data = self._data()
        return {"type": self.NAME,
                "message": str(self),
                "data": data}

    @abc.abstractmethod
    def _data(self) -> dict[str, Any]:
        """Returns a dictionary of the data associated with this event."""
        ...


@_attr.s(frozen=True, slots=True, str=False)
class BuildStarted(DarjeelingEvent):
    """An attempt to build a candidate patch has started."""
    NAME = "build-started"
    candidate: _Candidate = _attr.ib()

    def __str__(self) -> str:
        return f"building candidate patch [{self.candidate.id}]"

    def _data(self) -> dict[str, Any]:
        return {"candidate": {"id": self.candidate.id}}


@_attr.s(frozen=True, slots=True, str=False)
class BuildFinished(DarjeelingEvent):
    """An attempt to build a candidate patch has finished."""
    NAME = "build-finished"
    candidate: _Candidate = _attr.ib()
    outcome: _BuildOutcome = _attr.ib()

    def __str__(self) -> str:
        if not self.outcome.successful:
            prefix = "failed to build"
        else:
            prefix = "successfully built"

        s = (f"{prefix} candidate patch [{self.candidate.id}]"
             f" after {self.outcome.time_taken:.3f} seconds.")
        return s

    def _data(self) -> dict[str, Any]:
        return {"candidate": {"id": self.candidate.id},
                "outcome": self.outcome.to_dict()}


@_attr.s(frozen=True, slots=True, str=False)
class TestExecutionStarted(DarjeelingEvent):
    """A test for a given candidate patch has started executing."""
    NAME = "test-execution-started"
    candidate: _Candidate = _attr.ib()
    test: _Test = _attr.ib()

    def __str__(self) -> str:
        return (f"executing test [{self.test.name}]"
                f" for candidate patch [{self.candidate.id}]")

    def _data(self) -> dict[str, Any]:
        return {"candidate": {"id": self.candidate.id},
                "test": self.test.name}


@_attr.s(frozen=True, slots=True, str=False)
class TestExecutionFinished(DarjeelingEvent):
    """A test for a given candidate patch has finished executing."""
    NAME = "test-execution-finished"
    candidate: _Candidate = _attr.ib()
    test: _Test = _attr.ib()
    outcome: _TestOutcome = _attr.ib()

    def __str__(self) -> str:
        status = "passed" if self.outcome.successful else "failed"
        return (f"test {status} [{self.test.name}]"
                f" for candidate patch [{self.candidate.id}]")

    def _data(self) -> dict[str, Any]:
        return {"candidate": {"id": self.candidate.id},
                "test": self.test.name,
                "outcome": self.outcome.to_dict()}


@_attr.s(frozen=True, slots=True, str=False)
class TestExecutionError(DarjeelingEvent):
    """An unexpected error when executing a test."""
    NAME = "test-execution-error"
    candidate: _Candidate = _attr.ib()
    test: _Test = _attr.ib()
    error: Exception = _attr.ib()

    def __str__(self) -> str:
        return ("an unexpected error occurred when executing "
                f"test [{self.test.name}] "
                f"for candidate [{self.candidate}]:\n{self.error!s}")

    def _data(self) -> dict[str, Any]:
        return {"candidate": {"id": self.candidate.id},
                "test": self.test.name,
                "error": str(self.error)}


@_attr.s(frozen=True, slots=True, str=False)
class CandidateEvaluationStarted(DarjeelingEvent):
    """Evaluation of a given candidate patch has started."""
    NAME = "candidate-evaluation-started"
    candidate: _Candidate = _attr.ib()

    def __str__(self) -> str:
        return f"evaluating candidate patch [{self.candidate.id}]"

    def _data(self) -> dict[str, Any]:
        return {"candidate": {"id": self.candidate.id}}


@_attr.s(frozen=True, slots=True, str=False)
class CandidateEvaluationFinished(DarjeelingEvent):
    """Evaluation of a given candidate patch has finished."""
    NAME = "candidate-evaluation-started"
    candidate: _Candidate = _attr.ib()
    outcome: _CandidateOutcome = _attr.ib()

    def __str__(self) -> str:
        if self.outcome.is_repair:
            return f"found acceptable patch [{self.candidate.id}]"
        else:
            return f"rejected candidate patch [{self.candidate.id}]"

    def _data(self) -> dict[str, Any]:
        return {"candidate": {"id": self.candidate.id},
                "outcome": self.outcome.to_dict()}


@_attr.s(frozen=True, slots=True, str=False)
class CandidateEvaluationError(DarjeelingEvent):
    """An unexpected error occurred during evaluation of a candidate patch."""
    NAME = "candidate-evaluation-error"
    candidate: _Candidate = _attr.ib()
    error: Exception = _attr.ib()

    def __str__(self) -> str:
        return (f"unexpected error during evaluation of candidate patch"
                f" [{self.candidate.id}]: {self.error!s}")

    def _data(self) -> dict[str, Any]:
        return {"candidate": {"id": self.candidate.id},
                "error": str(self.error)}
