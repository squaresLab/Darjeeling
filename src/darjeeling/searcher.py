from typing import Iterable, Iterator, Optional, List
from mypy_extensions import NoReturn
from timeit import default_timer as timer
import logging
import datetime
import threading
import time
import signal

import bugzoo

from .core import FileLine
from .candidate import Candidate
from .problem import Problem
from .outcome import OutcomeManager
from .exceptions import BuildFailure

logger = logging.getLogger(__name__)  # type: logging.Logger

__all__ = ['Searcher']


class Shutdown(Exception):
    pass


class Searcher(object):
    def __init__(self,
                 bugzoo: bugzoo.BugZoo,
                 problem: Problem,
                 candidates: Iterable[Candidate],
                 *,
                 threads: int = 1,
                 time_limit: Optional[datetime.timedelta] = None,
                 candidate_limit: Optional[int] = None
                 ) -> None:
        """
        Constructs a new searcher for a given source of candidate patches.

        Parameters:
            bugzoo: a connection to the BugZoo server that should be used to
                evaluate candidate patches.
            problem: a description of the problem.
            candidates: a source of candidate patches.
            threads: the number of threads that should be made available to
                the search process.
            time_limit: an optional limit on the amount of time given to the
                searcher.
            candidate_limit: an optional limit on the number of candidate
                patches that may be generated.
        """
        logger.debug("constructed searcher")
        assert time_limit is None or time_limit > datetime.timedelta(), \
            "if specified, time limit should be greater than zero."

        self.__bugzoo = bugzoo
        self.__problem = problem
        self.__candidates = candidates
        self.__time_limit = time_limit
        self.__candidate_limit = candidate_limit
        self.__num_threads = threads
        self.__outcomes = OutcomeManager()

        # records the time at which the current iteration begun
        self.__time_iteration_begun = None  # type: ignore

        self.__lock_candidates = threading.Lock()  # type: threading.Lock
        self.__counter_candidates = 0
        self.__counter_tests = 0
        self.__exhausted_candidates = False
        self.__time_running = datetime.timedelta()
        self.__error_occurred = False
        self.__searching = False
        self.__found_patches = []  # type: List[Candidate]
        self.__history = []  # type: List[Candidate]
        logger.debug("constructed searcher")

    @property
    def history(self) -> List[Candidate]:
        """
        Returns an ordered list of all of the candidate patches that have been
        explored by this search process.
        """
        return self.__history.copy()

    @property
    def outcomes(self) -> OutcomeManager:
        """
        Provides a log of the outcomes of candidate patch build attempts and
        test executions.
        """
        return self.__outcomes

    @property
    def paused(self) -> bool:
        """
        Indicates whether this searcher is paused.
        """
        return (self.__found_patches != []) or self.exhausted

    @property
    def exhausted(self) -> bool:
        """
        Indicates whether or not the resources available to this searcher have
        been exhausted.
        """
        if self.__error_occurred:
            return True
        if self.__exhausted_candidates:
            return True
        if self.__time_limit is not None:
            if self.time_running > self.__time_limit:  # type: ignore
                return True
        if self.__candidate_limit is not None:
            if self.__counter_candidates > self.__candidate_limit:
                return True
        return False

    @property
    def num_test_evals(self) -> int:
        """
        The number of test case evaluations that have been performed during
        this search process.
        """
        return self.__counter_tests

    @property
    def num_candidate_evals(self) -> int:
        """
        The number of candidate patches that have been evaluated over the
        course of this search process.
        """
        return self.__counter_candidates

    @property
    def time_limit(self) -> Optional[datetime.timedelta]:
        """
        An optional limit on the length of time that may be spent searching
        for patches.
        """
        return self.__time_limit

    @property
    def time_running(self) -> datetime.timedelta:
        """
        The amount of time that has been spent searching for patches.
        """
        duration_delta = self.__time_running
        if self.__searching:
            time_now = timer()
            iteration_secs = time_now - self.__time_iteration_begun  # type: ignore
            iteration_delta = datetime.timedelta(seconds=iteration_secs)  # type: datetime.timedelta
            duration_delta = duration_delta + iteration_delta
        logger.debug("time running: %.2f minutes", duration_delta.seconds / 60)
        return duration_delta

    def stop(self) -> None:
        # FIXME just use an event to communicate when to stop
        self.__error_occurred = True

    def __iter__(self) -> Iterator[Candidate]:
        # time at which the last repair was found or the search was started
        self.__time_last_repair = timer()
        self.__paused_timer = False
        self.__offset_timer = 0.0

        for _ in self.__num_threads:
            try:
                self.evaluate(next(self.__candidates))
            except StopIteration:
                logger.info("all candidate patches have been exhausted")
                self.__exhausted = True
                break

        for candidate, outcome in evaluator.as_completed():
            if outcome.is_repair:
                # increment time_offset
                time_now = timer()
                self.__time_offset += time_now - self.__time_last_repair
                self.__time_last_repair = time_now
                self.__timer_is_paused = True

                yield candidate

                time_since_last_repair = timer()
                self.__paused = False

            if not self.__exhausted:
                try:
                    self.evaluate(next(self.__candidates))
                except StopIteration:
                    logger.info("all candidate patches have been exhausted")
                    self.__exhausted = True
                    break

    def __next__(self) -> Candidate:
        """
        Searches for the next acceptable patch.

        Returns:
            the next patch that passes all tests.

        Raises:
            StopIteration: if the search space or available resources have
                been exhausted.
        """
        self.__time_iteration_begun = timer()  # type: ignore
        for candidate, outcome:

        duration_iteration = timer() - self.__time_iteration_begun  # type: ignore
        self.__time_running += datetime.timedelta(seconds=duration_iteration)

        raise StopIteration
