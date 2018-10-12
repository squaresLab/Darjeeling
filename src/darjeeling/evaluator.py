__all__ = ['Evaluator']

from typing import Tuple, List, Optional
from timeit import default_timer as timer
from concurrent.futures import Future
import logging
import concurrent.futures

from bugzoo import Client as BugZooClient
from bugzoo.core import FileLine

from .candidate import Candidate
from .outcome import CandidateOutcome, OutcomeManager
from .problem import Problem
from .exceptions import BuildFailure

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)


class Evaluator(object):
    def __init__(self,
                 client_bugzoo: BugZooClient,
                 problem: Problem,
                 *,
                 num_workers: int = 1,
                 outcomes: Optional[OutcomeManager] = None
                 ) -> None:
        self.__bugzoo = client_bugzoo
        self.__problem = problem
        self.__executor = \
            concurrent.futures.ThreadPoolExecutor(max_workers=num_workers)
        self.__num_workers = num_workers
        if outcomes:
            self.__outcomes = outcomes
        else:
            self.__outcomes = OutcomeManager()

        self.__counter_tests = 0
        self.__counter_candidates = 0

    @property
    def outcomes(self) -> OutcomeManager:
        return self.__outcomes

    @property
    def num_workers(self) -> int:
        return self.__num_workers

    @property
    def num_test_evals(self) -> int:
        """
        The number of test case evaluations performed by this evaluator.
        """
        return self.__counter_tests

    @property
    def num_candidate_evals(self) -> int:
        """
        The number of candidate evaluations performed by this evaluator.
        """
        return self.__counter_candidates

    def _evaluate(self, candidate: Candidate) -> None:
        self.__counter_candidates += 1

        patch = candidate.to_diff(self.__problem)
        line_coverage_by_test = self.__problem.coverage
        lines_changed = \
            candidate.lines_changed(self.__problem)  # type: List[FileLine]
        logger.info("evaluating candidate: %s\n%s\n", candidate, patch)

        bz = self.__bugzoo
        logger.debug("building candidate: %s", candidate)
        time_build_start = timer()
        try:
            container = self.__problem.build_patch(patch)
            logger.debug("built candidate: %s", candidate)
            self.outcomes.record_build(candidate,
                                       True,
                                       timer() - time_build_start)

            # TODO perform test ordering
            logger.debug("executing tests for candidate: %s", candidate)
            for test in self.__problem.tests:
                # skip redundant tests
                # FIXME for some search algos, we need to record this info
                test_line_coverage = line_coverage_by_test[test.name]
                if not any(line in test_line_coverage for line in lines_changed):
                    logger.debug("skipping redundant test: %s [%s]",
                                 test.name, candidate)
                    continue

                logger.debug("executing test: %s [%s]", test.name, candidate)
                self.__counter_tests += 1
                outcome = bz.containers.test(container, test)

                self.outcomes.record_test(candidate, test.name, outcome)
                if not outcome.passed:
                    logger.debug("* test failed: %s (%s)", test.name, candidate)
                    # TODO early termination?
                    return
                logger.debug("* test passed: %s (%s)", test.name, candidate)

        except BuildFailure:
            logger.debug("failed to build candidate: %s", candidate)
            self.outcomes.record_build(candidate,
                                       False,
                                       timer() - time_build_start)
        finally:
            logger.info("evaluated candidate: %s", candidate)
            if container:
                del bz.containers[container.uid]
                logger.debug("destroyed container for candidate: %s", candidate)

    def evaluate(self,
                 candidate: Candidate
                 ) -> Tuple[Candidate, CandidateOutcome]:
        if candidate in self.outcomes:
            return (candidate, self.outcomes[candidate])
        self._evaluate(candidate)
        return (candidate, self.outcomes[candidate])

    def submit(self,
               candidate: Candidate
               ) -> 'Future[Tuple[Candidate, CandidateOutcome]]':
        return self.__executor.submit(self.evaluate, candidate)
