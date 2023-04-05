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
    'CandidateOutcomeStore'
)

from typing import Any, Dict, Iterator, Mapping

import attr

from .core import BuildOutcome, TestOutcome, TestOutcomeSet
from .candidate import Candidate


@attr.s(frozen=True, slots=True, auto_attribs=True)
class CandidateOutcome:
    """Records the outcome of a candidate patch evaluation."""
    build: BuildOutcome
    tests: TestOutcomeSet
    is_repair: bool
    heldout_tests: TestOutcomeSet
    is_general_repair: bool

    def with_test_outcome(self,
                          test: str,
                          successful: bool,
                          time_taken: float,
                          is_heldout: bool,
                          ) -> 'CandidateOutcome':
        outcome = TestOutcome(successful, time_taken)
        test_outcomes = None
        heldout_test_outcomes = None
        if heldout:
            heldout_test_outcomes = self.heldout_tests.with_outcome(test, outcome)
        else:
            test_outcomes = self.tests.with_outcome(test, outcome)
        return CandidateOutcome(
                self.build, test_outcomes, self.is_repair, 
                heldout_test_outcomes, self.is_general_repair
            )

    def merge(self,
              other: 'CandidateOutcome'
              ) -> 'CandidateOutcome':
        other_is_repair = all(other.tests[t].successful for t in other.tests)
        other_is_general_repair = all(other.heldout_tests[t].successful for t in other.heldout_tests)
        return CandidateOutcome(self.build,
                                self.tests.merge(other.tests),
                                self.heldout_tests.merge(other.heldout_tests),
                                self.is_repair and other_is_repair,
                                self.is_general_repair and other_is_general_repair)

    def to_dict(self) -> Dict[str, Any]:
        return {'build': self.build.to_dict(),
                'tests': self.tests.to_dict(),
                'is-repair': self.is_repair,
                'heldout_tests': self.heldout_tests.to_dict(),
                'is-general-repair': self.is_general_repair}


class CandidateOutcomeStore(Mapping[Candidate, CandidateOutcome]):
    """Maintains a record of candidate patch evaluation outcomes."""
    def __init__(self) -> None:
        self.__outcomes: Dict[Candidate, CandidateOutcome] = {}

    def __repr__(self) -> str:
        return self.__class__.__name__

    def __contains__(self, candidate: Any) -> bool:
        if not isinstance(candidate, Candidate):
            return False
        return candidate in self.__outcomes

    def __getitem__(self, candidate: Candidate) -> CandidateOutcome:
        return self.__outcomes[candidate]

    def __iter__(self) -> Iterator[Candidate]:
        yield from self.__outcomes

    def __len__(self) -> int:
        """Returns a count of the number of represented candidate patches."""
        return len(self.__outcomes)

    def record(self,
               candidate: Candidate,
               outcome: CandidateOutcome
               ) -> None:
        if candidate not in self.__outcomes:
            self.__outcomes[candidate] = outcome
        else:
            self.__outcomes[candidate] = \
                self.__outcomes[candidate].merge(outcome)
