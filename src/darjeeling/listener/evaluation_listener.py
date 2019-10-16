# -*- coding: utf-8 -*-
__all__ = ('EvaluationListener',)

import abc

from ..core import Test, TestOutcome, BuildOutcome
from ..candidate import Candidate
from ..outcome import CandidateOutcome


class EvaluationListener(abc.ABC):
    """Provides an interface for listening to patch evaluation events."""
    @abc.abstractmethod
    def on_test_finished(self,
                         candidate: Candidate,
                         test: Test,
                         outcome: TestOutcome
                         ) -> None:
        """Called when a test execution has finished for a candidate patch."""
        ...

    @abc.abstractmethod
    def on_test_started(self, candidate: Candidate, test: Test) -> None:
        """Called when a test execution has begun for a candidate patch."""
        ...

    @abc.abstractmethod
    def on_build_started(self, candidate: Candidate) -> None:
        """Called when an attempt to build a candidate patch has begun."""
        ...

    @abc.abstractmethod
    def on_build_finished(self,
                          candidate: Candidate,
                          outcome: BuildOutcome
                          ) -> None:
        """Called when an attempt to build a candidate patch has finished."""
        ...

    @abc.abstractmethod
    def on_candidate_started(self, candidate: Candidate) -> None:
        """Called when the evaluation of a candidate patch has begun."""
        ...

    @abc.abstractmethod
    def on_candidate_finished(self,
                              candidate: Candidate,
                              outcome: CandidateOutcome
                              ) -> None:
        """Called when the evaluation of a candidate patch has finished."""
        ...
