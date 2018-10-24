from typing import Dict, Optional, Iterator
import attr

from bugzoo.core import TestOutcome as BugZooTestOutcome
from bugzoo.compiler import CompilationOutcome as BugZooBuildOutcome

from .candidate import Candidate

__all__ = [
    'TestOutcome',
    'TestOutcomeSet',
    'BuildOutcome',
    'CandidateOutcome',
    'OutcomeManager'
]


@attr.s(frozen=True)
class TestOutcome(object):
    """
    Records the outcome of a test execution.
    """
    successful = attr.ib(type=bool)
    time_taken = attr.ib(type=float)


@attr.s(frozen=True)
class BuildOutcome(object):
    """
    Records the outcome of a build attempt.
    """
    successful = attr.ib(type=bool)
    time_taken = attr.ib(type=float)


class TestOutcomeSet(object):
    """
    Records the outcome of different test executions for a single patch.
    """
    def __init__(self,
                 outcomes: Optional[Dict[str, TestOutcome]] = None
                 ) -> None:
        if outcomes is None:
            outcomes = {}
        self.__outcomes = outcomes # type: Dict[str, TestOutcome]

    def __iter__(self) -> Iterator[str]:
        return self.__outcomes.keys().__iter__()

    def __getitem__(self, test: str) -> TestOutcome:
        return self.__outcomes[test]

    def with_outcome(self, test: str, outcome: TestOutcome) -> 'TestOutcomeSet':
        outcomes = self.__outcomes.copy()
        outcomes[test] = outcome
        return TestOutcomeSet(outcomes)

    def merge(self, other: 'TestOutcomeSet') -> 'TestOutcomeSet':
        outcomes = self.__outcomes.copy()
        for test_name in other:
            outcomes[test_name] = other[test_name]
        return TestOutcomeSet(outcomes)


@attr.s(frozen=True)
class CandidateOutcome(object):
    """
    Records the outcome of a candidate patch evaluation.
    """
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
