from typing import Dict, Optional, Iterator

from bugzoo.testing.base import TestOutcome as BugZooTestOutcome
from bugzoo.compiler import CompilationOutcome as BugZooBuildOutcome

from .candidate import Candidate

__all__ = [
    'BuildOutcome',
    'TestOutcome',
    'TestOutcomeSet',
    'CandidateOutcome',
    'OutcomeManager'
]


class BuildOutcome(object):
    """
    Records the outcome of an attempted build.
    """
    def __init__(self, successful: bool, time_taken: float) -> None:
        self.__time_taken = time_taken
        self.__successful = successful

    @property
    def time_taken(self) -> float:
        return self.__time_taken

    @property
    def successful(self) -> bool:
        return self.__successful


class TestOutcome(object):
    """
    Records the outcome of a test execution.
    """
    def __init__(self, successful: bool, time_taken: float) -> None:
        self.__successful = successful
        self.__time_taken = time_taken

    @property
    def successful(self) -> bool:
        return self.__successful

    @property
    def time_taken(self) -> float:
        return self.__time_taken


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


class CandidateOutcome(object):
    """
    Records the outcome of a candidate patch evaluation.
    """
    def __init__(self, build: BuildOutcome, tests: TestOutcomeSet) -> None:
        self.__build = build
        self.__tests = tests

    @property
    def build(self) -> BuildOutcome:
        return self.__build

    @property
    def tests(self) -> TestOutcomeSet:
        return self.__tests

    def with_test_outcome(self,
                          test: str,
                          successful: bool,
                          time_taken: float
                          ) -> 'CandidateOutcome':
        outcome = TestOutcome(successful, time_taken)
        test_outcomes = self.__tests.with_outcome(test, outcome)
        return CandidateOutcome(self.__build, test_outcomes)


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
                     build_outcome: BugZooBuildOutcome
                     ) -> None:
        b = BuildOutcome(build_outcome.successful,
                         build_outcome.response.duration)
        c = CandidateOutcome(b, TestOutcomeSet())
        self.__outcomes[candidate] = c

    def record_test(self,
                    candidate: Candidate,
                    test_id: str,
                    test_outcome: BugZooTestOutcome
                    ) -> None:
        # TODO  race condition if there can be simultaneous test evaluations
        #       for a given patch; for now, that's not possible.
        candidate_outcome = self.__outcomes[candidate]
        candidate_outcome = candidate_outcome.with_test_outcome(test_id,
                                                                test_outcome.passed,
                                                                test_outcome.duration)
        self.__outcomes[candidate] = candidate_outcome
