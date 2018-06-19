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


@attr.s(frozen=True)
class CandidateOutcome(object):
    """
    Records the outcome of a candidate patch evaluation.
    """
    build = attr.ib(type=BuildOutcome)
    tests = attr.ib(type=TestOutcomeSet)

    def with_test_outcome(self,
                          test: str,
                          successful: bool,
                          time_taken: float
                          ) -> 'CandidateOutcome':
        outcome = TestOutcome(successful, time_taken)
        test_outcomes = self.tests.with_outcome(test, outcome)
        return CandidateOutcome(self.build, test_outcomes)


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

    def record_build(self,
                     candidate: Candidate,
                     successful: bool,
                     time_taken: float
                     ) -> None:
        outcome_build = BuildOutcome(successful, time_taken)
        c = CandidateOutcome(outcome_build, TestOutcomeSet())
        self.__outcomes[candidate] = c

    def record_test(self,
                    candidate: Candidate,
                    test_id: str,
                    test_outcome: BugZooTestOutcome
                    ) -> None:
        # TODO  race condition if there can be simultaneous test evaluations
        #       for a given patch; for now, that's not possible.
        candidate_outcome = self.__outcomes[candidate]
        candidate_outcome = \
            candidate_outcome.with_test_outcome(test_id,
                                                test_outcome.passed,
                                                test_outcome.duration)
        self.__outcomes[candidate] = candidate_outcome
