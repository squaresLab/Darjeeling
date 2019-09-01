# -*- coding: utf-8 -*-
"""
This module implements data structures and containers for describing the
outcome of test and build attempts.
"""
__all__ = (
    'TestOutcome',
    'TestOutcomeSet',
    'BuildOutcome',
    'CandidateOutcome',
    'OutcomeManager'
)

from typing import Dict, Optional, Iterator

import attr

from .core import TestOutcome, TestOutcomeSet, BuildOutcome
from .candidate import Candidate


@attr.s(frozen=True)
class CandidateOutcome(object):
    """Records the outcome of a candidate patch evaluation."""
    build = attr.ib(type=BuildOutcome)
    tests = attr.ib(type=TestOutcomeSet)
    is_repair = attr.ib(type=bool)

    def with_test_outcome(self,
                          test: str,
                          successful: bool,
                          time_taken: float
                          ) -> 'CandidateOutcome':
        outcome = TestOutcome(successful, time_taken)
        test_outcomes = self.tests.with_outcome(test, outcome)
        return CandidateOutcome(self.build, test_outcomes, self.is_repair)

    def merge(self,
              other: 'CandidateOutcome'
              ) -> 'CandidateOutcome':
        other_is_repair = all(other.tests[t].successful for t in other.tests)
        return CandidateOutcome(self.build,
                                self.tests.merge(other.tests),
                                self.is_repair and other_is_repair)


class OutcomeManager(object):
    # FIXME hash candidate outcomes
    def __init__(self) -> None:
        self.__outcomes = {} # type: Dict[Candidate, CandidateOutcome]

    def __getitem__(self, candidate: Candidate) -> CandidateOutcome:
        return self.__outcomes[candidate]

    def __iter__(self) -> Iterator[Candidate]:
        """
        Returns an iterator over the candidate patches whose outcomes are
        stored by this manager.
        """
        return self.__outcomes.keys().__iter__()

    def record(self,
               candidate: Candidate,
               outcome: CandidateOutcome
               ) -> None:
        if candidate not in self.__outcomes:
            self.__outcomes[candidate] = outcome
        else:
            self.__outcomes[candidate] = \
                self.__outcomes[candidate].merge(outcome)
