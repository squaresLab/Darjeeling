__all__ = ['Evaluator']

from typing import Tuple, List, Optional, Iterator, Set, Union, FrozenSet
from timeit import default_timer as timer
from concurrent.futures import Future
import math
import logging
import queue
import threading
import concurrent.futures
import random

import bugzoo
from bugzoo import Client as BugZooClient
from bugzoo.core import FileLine
from bugzoo.core.test import TestCase as Test
from bugzoo.core.test import TestOutcome as BugZooTestOutcome

from .candidate import Candidate
from .outcome import CandidateOutcome, \
                     OutcomeManager, \
                     TestOutcomeSet, \
                     TestOutcome, \
                     BuildOutcome
from .problem import Problem
from .exceptions import BuildFailure
from .util import Stopwatch

Evaluation = Tuple[Candidate, CandidateOutcome]

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)


class Evaluator(object):
    def __init__(self,
                 client_bugzoo: BugZooClient,
                 problem: Problem,
                 *,
                 num_workers: int = 1,
                 terminate_early: bool = True,
                 sample_size: Optional[Union[float, int]] = None,
                 outcomes: Optional[OutcomeManager] = None
                 ) -> None:
        self.__bugzoo = client_bugzoo
        self.__problem = problem
        self.__executor = \
            concurrent.futures.ThreadPoolExecutor(max_workers=num_workers)
        self.__num_workers = num_workers
        self.__terminate_early = terminate_early

        self.__tests_failing = \
            frozenset(self.__problem.failing_tests)  # type: FrozenSet[Test]
        self.__tests_passing = \
            frozenset(self.__problem.passing_tests)  # type: FrozenSet[Test]

        # if the sample size is passed as a fraction, convert that fraction
        # to an integer
        if isinstance(sample_size, float):
            num_passing = len(self.__tests_passing)
            sample_size = math.ceil(num_passing * sample_size)
            self.__sample_size = sample_size  # type: Optional[int]
        else:
            self.__sample_size = sample_size

        if outcomes:
            self.__outcomes = outcomes
        else:
            self.__outcomes = OutcomeManager()

        self.__lock = threading.Lock()
        self.__queue_evaluated = queue.Queue()  # type: queue.Queue
        self.__num_running = 0
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

    def _order_tests(self, tests: Set[Test]) -> List[Test]:
        # FIXME implement ordering strategies
        return list(tests)

    def _select_tests(self) -> Tuple[List[Test], List[Test]]:
        """
        Computes a test sequence for a candidate evaluation.
        """
        # sample passing tests
        sample = set()  # type: Set[Test]
        if self.__sample_size:
            sample = \
                set(random.sample(self.__tests_passing, self.__sample_size))
        else:
            sample = set(self.__tests_passing)

        selected = sample | self.__tests_failing  # type: Set[Test]
        remainder = set(self.__tests_passing - sample)  # type: Set[Test]

        # order tests
        ordered_selected = self._order_tests(selected)  # type: List[Test]
        ordered_remainder = self._order_tests(remainder)  # type: List[Test]
        return ordered_selected, ordered_remainder

    def _filter_redundant_tests(self,
                                candidate: Candidate,
                                tests: List[Test]
                                ) -> Tuple[List[Test], Set[Test]]:
        line_coverage_by_test = self.__problem.coverage
        lines_changed = candidate.lines_changed(self.__problem)
        keep = []  # type: List[Test]
        drop = set()  # type: Set[Test]
        for test in tests:
            test_line_coverage = line_coverage_by_test[test.name]
            if not any(line in test_line_coverage for line in lines_changed):
                drop.add(test)
            else:
                keep.append(test)
        return (keep, drop)

    def _run_test(self,
                  container: bugzoo.Container,
                  candidate: Candidate,
                  test: Test
                  ) -> TestOutcome:
        """
        Runs a test for a given candidate patch using a provided container.
        """
        logger.debug("executing test: %s [%s]", test.name, candidate)
        self.__counter_tests += 1
        bz = self.__bugzoo
        bz_outcome = \
            bz.containers.test(container, test)  # type: BugZooTestOutcome
        if not bz_outcome.passed:
            logger.debug("* test failed: %s (%s)", test.name, candidate)
        else:
            logger.debug("* test passed: %s (%s)", test.name, candidate)
        return TestOutcome(bz_outcome.passed, bz_outcome.duration)

    def _evaluate(self,
                  candidate: Candidate
                  ) -> CandidateOutcome:
        bz = self.__bugzoo

        patch = candidate.to_diff(self.__problem)
        logger.info("evaluating candidate: %s\n%s\n", candidate, patch)

        # select a subset of tests to use for this evaluation
        tests, remainder = self._select_tests()
        tests, redundant  = self._filter_redundant_tests(candidate, tests)

        # compute outcomes for redundant tests
        test_outcomes = TestOutcomeSet({
            t.name: TestOutcome(True, 0.0) for t in redundant
        })  # type: TestOutcomeSet

        # if we have evidence that this patch is not a complete repair,
        # there is no need to extend beyond the test sample in the event
        # that all tests in the sample are successful
        known_bad_patch = False

        if candidate in self.outcomes:
            logger.info("found candidate in cache: %s", candidate)
            cached_outcome = self.outcomes[candidate]
            known_bad_patch |= not cached_outcome.is_repair

            if not cached_outcome.build.successful:
                return cached_outcome

            # don't bother executing tests for which we already have results
            filtered_tests = []  # type: List[Test]
            for test in tests:
                if test.name in cached_outcome.tests:
                    test_outcome = cached_outcome.tests[test.name]
                    test_outcomes = \
                        test_outcomes.with_outcome(test.name, test_outcome)
                else:
                    filtered_tests.append(test)
            tests = filtered_tests
            logger.debug("filtered tests: %s", tests)

            # if no tests remain, construct a partial view of the candidate
            # outcome
            if not tests:
                return CandidateOutcome(cached_outcome.build,
                                        test_outcomes,
                                        not known_bad_patch)

        self.__counter_candidates += 1
        logger.debug("building candidate: %s", candidate)
        timer_build = Stopwatch()
        timer_build.start()
        container = None  # type: Optional[Candidate]
        try:
            container = self.__problem.build_patch(patch)
            outcome_build = BuildOutcome(True, timer_build.duration)
            logger.debug("built candidate: %s", candidate)
            logger.debug("executing tests for candidate: %s", candidate)
            for test in tests:
                if self.__terminate_early and known_bad_patch:
                    break
                test_outcome = self._run_test(container, candidate, test)
                test_outcomes = \
                    test_outcomes.with_outcome(test.name, test_outcome)
                known_bad_patch |= not test_outcome.successful

            # if there is no evidence that this patch fails any tests, execute
            # all remaining tests to determine whether or not this patch is
            # an acceptable repair
            #
            # FIXME check if outcome is redundant!
            if not known_bad_patch:
                for test in remainder:
                    if known_bad_patch:
                        break
                    test_outcome = self._run_test(container, candidate, test)
                    test_outcomes = \
                        test_outcomes.with_outcome(test.name, test_outcome)
                    known_bad_patch |= not test_outcome.successful

            return CandidateOutcome(outcome_build,
                                    test_outcomes,
                                    not known_bad_patch)
        except BuildFailure:
            logger.debug("failed to build candidate: %s", candidate)
            outcome_build = BuildOutcome(False, timer_build.duration)
            return CandidateOutcome(outcome_build,
                                    TestOutcomeSet(),
                                    False)
        except Exception:
            logger.exception("unexpected exception when evaluating candidate: %s",  # noqa: pycodestyle
                             candidate)
            raise
        finally:
            logger.info("evaluated candidate: %s", candidate)
            if container:
                del bz.containers[container.id]
                logger.debug("destroyed container for candidate: %s", candidate)

    def evaluate(self,
                 candidate: Candidate
                 ) -> Evaluation:
        """
        Evaluates a given candidate patch.
        """
        # FIXME return an evaluation error
        try:
            outcome = self._evaluate(candidate)
        except Exception:
            m = "unexpected error occurred when evaluating candidate [{}]"
            m = m.format(candidate.id)
            logger.exception(m)

        self.outcomes.record(candidate, outcome)
        with self.__lock:
            self.__queue_evaluated.put((candidate, outcome))
            self.__num_running -= 1
        return (candidate, outcome)

    def submit(self,
               candidate: Candidate
               ) -> 'Future[Evaluation]':
        """
        Schedules a candidate patch evaluation.
        """
        with self.__lock:
            self.__num_running += 1
        future = self.__executor.submit(self.evaluate, candidate)
        return future

    def as_completed(self) -> Iterator[Evaluation]:
        q = self.__queue_evaluated  # type: queue.Queue
        while True:
            with self.__lock:
                if q.empty() and self.__num_running == 0:
                    break
            yield q.get()
