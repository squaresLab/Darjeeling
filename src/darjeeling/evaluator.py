__all__ = ['Evaluator']

from typing import Tuple
from concurrent.futures import Future
import logging
import concurrent.futures

import attr
from bugzoo import Client as BugZooClient

from .candidate import Candidate
from .outcome import CandidateOutcome, OutcomeManager
from .problem import Problem

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)


@attr.ib(frozen=True)
class Evaluator(object):
    def __init__(self,
                 client_bugzoo: BugZooClient,
                 problem: Problem,
                 num_workers: int = 1
                 ) -> None:
        self.__bugzoo = client_bugzoo
        self.__problem = problem
        self.__executor = \
            concurrent.futures.ThreadPoolExecutor(max_workers=num_workers)
        self.__num_workers = num_workers
        self.outcomes = OutcomeManager()

        self.__counter_tests = 0

    @property
    def num_workers(self) -> int:
        return self.__num_workers

    def _evaluate(self, candidate: Candidate) -> None:
        patch = candidate.to_diff(self.__problem)
        logger.info("evaluating candidate: %s\n%s\n", candidate, patch)

        bz = self.__bugzoo
        logger.debug("building candidate: %s", candidate)
        time_build_start = timer()
        try:
            container = self.__problem.build_patch(patch)
            logger.debug("built candidate: %s", candidate)
            self.outcomes.record_build(candidate, True, timer() - time_build_start)

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
                    return True
                logger.debug("* test passed: %s (%s)", test.name, candidate)

        except BuildFailure:
            logger.debug("failed to build candidate: %s", candidate)
            self.outcomes.record_build(candidate, False, timer() - time_build_start)
            return True
        finally:
            logger.info("evaluated candidate: %s", candidate)
            if container:
                del bz.containers[container.uid]
                logger.debug("destroyed container for candidate: %s", candidate)

    def evaluate(self, candidate: Candidate) -> CandidateOutcome:
        if candidate in self.outcomes:
            return self.outcomes[candidate]

        self._evaluate(candidate)
        return self.outcomes[candidate]

    def submit(self,
               candidate: Candidate
               ) -> Future[Tuple[Candidate, CandidateOutcome]]:
        return self.__executor.submit(self.evaluate, candidate)
