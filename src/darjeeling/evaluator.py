"""Efficiently evaluates candidate patches and performs individual test executions."""
from __future__ import annotations

__all__ = ("Evaluator",)

import concurrent.futures
import math
import queue
import random
import threading
import typing
from collections.abc import Iterator, Sequence
from concurrent.futures import Future
from typing import Optional, Union

from loguru import logger

import darjeeling.exceptions as exc
from darjeeling.candidate import Candidate
from darjeeling.container import ProgramContainer
from darjeeling.core import Test
from darjeeling.events.event import (
    BuildFinished,
    BuildStarted,
    CandidateEvaluationError,
    CandidateEvaluationFinished,
    CandidateEvaluationStarted,
    TestExecutionError,
    TestExecutionFinished,
    TestExecutionStarted,
)
from darjeeling.events.producer import DarjeelingEventProducer

from .exceptions import BuildFailure
from .outcome import (
    BuildOutcome,
    CandidateOutcome,
    CandidateOutcomeStore,
    TestOutcome,
    TestOutcomeSet,
)
from .resources import ResourceUsageTracker
from .util import Stopwatch

if typing.TYPE_CHECKING:
    from .problem import Problem

Evaluation = tuple[Candidate, CandidateOutcome]


class Evaluator(DarjeelingEventProducer):
    def __init__(self,
                 problem: Problem,
                 resources: ResourceUsageTracker,
                 *,
                 num_workers: int = 1,
                 terminate_early: bool = True,
                 sample_size: Optional[Union[float, int]] = None,
                 outcomes: Optional[CandidateOutcomeStore] = None,
                 run_redundant_tests: bool = False,
                 ) -> None:
        super().__init__()
        self.__problem = problem
        self.__resources = resources
        self.__program = problem.program
        self.__test_suite = problem.test_suite
        self.__executor = \
            concurrent.futures.ThreadPoolExecutor(max_workers=num_workers)
        self.__num_workers = num_workers
        self.__terminate_early = terminate_early
        self.__outcomes = outcomes or CandidateOutcomeStore()
        self.__run_redundant_tests = run_redundant_tests

        self.__tests_failing: frozenset[Test] = \
            frozenset(self.__problem.failing_tests)
        self.__tests_passing: frozenset[Test] = \
            frozenset(self.__problem.passing_tests)

        # FIXME used the precomputed test ordering for now
        self.__test_ordering: Sequence[Test] = list(self.__problem.tests)

        # if the sample size is passed as a fraction, convert that fraction
        # to an integer
        if isinstance(sample_size, float):
            num_passing = len(self.__tests_passing)
            sample_size = math.ceil(num_passing * sample_size)
            self.__sample_size: Optional[int] = sample_size
        else:
            self.__sample_size = sample_size

        self.__lock = threading.Lock()
        self.__queue_evaluated: queue.Queue[tuple[Candidate, CandidateOutcome]] = queue.Queue()
        self.__num_running = 0

    @property
    def num_workers(self) -> int:
        return self.__num_workers

    def _order_tests(self, tests: set[Test]) -> list[Test]:
        """Prioritizes a given set of tests into a sequence."""
        # FIXME implement ordering strategies
        ordered: list[Test] = []
        for test in self.__test_ordering:
            if test in tests:
                ordered.append(test)
        return ordered

    def _select_tests(self) -> tuple[list[Test], list[Test]]:
        """Computes a test sequence for a candidate evaluation."""
        # sample passing tests
        sample: set[Test] = set()
        if self.__sample_size:
            sample = \
                set(random.sample(self.__tests_passing, self.__sample_size))  # type: ignore[arg-type]
        else:
            sample = set(self.__tests_passing)

        selected: set[Test] = sample | self.__tests_failing
        remainder: set[Test] = set(self.__tests_passing - sample)

        # order tests
        ordered_selected: list[Test] = self._order_tests(selected)
        ordered_remainder: list[Test] = self._order_tests(remainder)
        return ordered_selected, ordered_remainder

    def _filter_redundant_tests(self,
                                candidate: Candidate,
                                tests: list[Test],
                                ) -> tuple[list[Test], set[Test]]:
        line_coverage_by_test = self.__problem.coverage
        lines_changed = candidate.lines_changed()

        # if no lines are changed, retain all tests (fixes issue #128)
        if not lines_changed:
            return (tests, set())

        keep: list[Test] = []
        drop: set[Test] = set()
        for test in tests:
            test_line_coverage = line_coverage_by_test[test.name]
            if not any(line in test_line_coverage for line in lines_changed):
                drop.add(test)
            else:
                keep.append(test)
        return (keep, drop)

    def _run_test(self,
                  container: ProgramContainer,
                  candidate: Candidate,
                  test: Test,
                  ) -> TestOutcome:
        """Runs a test for a given patch using a provided container."""
        logger.debug(f"executing test: {test.name} [{candidate}]")
        self.dispatch(TestExecutionStarted(candidate, test))
        self.__resources.tests += 1

        # if an unexpected exception occurs during test execution, log the
        # event and report the test execution as a failure.
        timer = Stopwatch()
        timer.start()
        try:
            outcome = self.__program.execute(container, test)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as err:
            logger.exception("unexpected error when executing "
                             f"test [{test.name}] for "
                             f"candidate [{candidate}]")
            self.dispatch(TestExecutionError(candidate, test, err))
            outcome = TestOutcome(successful=False,
                                  time_taken=timer.duration)

        if not outcome.successful:
            logger.debug(f"* test failed: {test.name} ({candidate})")
        else:
            logger.debug(f"* test passed: {test.name} ({candidate})")
        self.dispatch(TestExecutionFinished(candidate, test, outcome))
        return outcome

    def _evaluate(self, candidate: Candidate) -> CandidateOutcome:
        outcomes = self.__outcomes
        patch = candidate.to_diff()
        logger.info(f"evaluating candidate: {candidate}\n{patch}\n")

        # select a subset of tests to use for this evaluation
        tests, remainder = self._select_tests()
        if not self.__run_redundant_tests:
            tests, redundant = self._filter_redundant_tests(candidate, tests)
        else:
            redundant = set()

        # compute outcomes for redundant tests
        test_outcomes = TestOutcomeSet({
            t.name: TestOutcome(True, 0.0) for t in redundant
        })  # type: TestOutcomeSet

        # if we have evidence that this patch is not a complete repair,
        # there is no need to extend beyond the test sample in the event
        # that all tests in the sample are successful
        known_bad_patch = False

        if candidate in outcomes:
            logger.info(f"found candidate in cache: {candidate}")
            cached_outcome = outcomes[candidate]
            known_bad_patch |= not cached_outcome.is_repair

            if not cached_outcome.build.successful:
                return cached_outcome

            # don't bother executing tests for which we already have results
            filtered_tests: list[Test] = []
            for test in tests:
                if test.name in cached_outcome.tests:
                    test_outcome = cached_outcome.tests[test.name]
                    test_outcomes = \
                        test_outcomes.with_outcome(test.name, test_outcome)
                else:
                    filtered_tests.append(test)
            tests = filtered_tests
            logger.debug(f"filtered tests: {tests}")

            # if no tests remain, construct a partial view of the candidate
            # outcome
            if not tests:
                return CandidateOutcome(cached_outcome.build,
                                        test_outcomes,
                                        not known_bad_patch)

        self.__resources.candidates += 1
        logger.debug(f"building candidate: {candidate}")
        self.dispatch(BuildStarted(candidate))
        timer_build = Stopwatch()
        timer_build.start()
        try:
            with self.__program.build(patch) as container:
                outcome_build = BuildOutcome(True, timer_build.duration)
                self.dispatch(BuildFinished(candidate, outcome_build))
                logger.debug(f"built candidate: {candidate}")
                logger.debug(f"executing tests for candidate: {candidate}")
                for test in tests:
                    if self.__terminate_early and known_bad_patch:
                        break
                    test_outcome = self._run_test(container, candidate, test)
                    test_outcomes = \
                        test_outcomes.with_outcome(test.name, test_outcome)
                    known_bad_patch |= not test_outcome.successful

                # if there is no evidence that this patch fails any tests,
                # execute all remaining tests to determine whether or not
                # this patch is an acceptable repair
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
            logger.debug(f"failed to build candidate: {candidate}")
            outcome_build = BuildOutcome(False, timer_build.duration)
            self.dispatch(BuildFinished(candidate, outcome_build))
            return CandidateOutcome(outcome_build,
                                    TestOutcomeSet(),
                                    False)
        except Exception:
            logger.exception("unexpected exception when evaluating candidate: {}",  # noqa: pycodestyle
                             candidate)
            raise
        finally:
            logger.info(f"evaluated candidate: {candidate}")

    def evaluate(self, candidate: Candidate) -> Evaluation:
        """Evaluates a given candidate patch."""
        outcomes = self.__outcomes
        self.dispatch(CandidateEvaluationStarted(candidate))
        try:
            outcome = self._evaluate(candidate)
        except Exception as err:
            m = "unexpected error occurred when evaluating candidate [{}]"
            logger.exception(m.format(candidate.id))
            self.dispatch(CandidateEvaluationError(candidate, err))
            raise exc.UnexpectedCandidateEvaluationError(candidate=candidate,
                                                         error=err)
        else:
            self.dispatch(CandidateEvaluationFinished(candidate, outcome))

        outcomes.record(candidate, outcome)
        with self.__lock:
            self.__queue_evaluated.put((candidate, outcome))
            self.__num_running -= 1
        return (candidate, outcome)

    def submit(self, candidate: Candidate) -> Future[Evaluation]:
        """Schedules a candidate patch evaluation."""
        with self.__lock:
            self.__num_running += 1
        future = self.__executor.submit(self.evaluate, candidate)
        return future

    def as_completed(self) -> Iterator[Evaluation]:
        q: queue.Queue[tuple[Candidate, CandidateOutcome]] = self.__queue_evaluated
        while True:
            with self.__lock:
                if q.empty() and self.__num_running == 0:
                    break
            yield q.get()
