from typing import Iterable, Iterator, Optional, List
from mypy_extensions import NoReturn
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
from .evaluator import Evaluator
from .exceptions import BuildFailure, SearchAlreadyStarted
from .util import Stopwatch

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)

__all__ = ['Searcher']


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
        logger.debug("constructing searcher")
        assert time_limit is None or time_limit > datetime.timedelta(), \
            "if specified, time limit should be greater than zero."

        self.__bugzoo = bugzoo
        self.__problem = problem
        self.__candidates = candidates
        self.__time_limit = time_limit
        self.__candidate_limit = candidate_limit
        self.__outcomes = OutcomeManager()
        self.__evaluator = Evaluator(bugzoo,
                                     problem,
                                     num_workers=threads,
                                     outcomes=self.__outcomes)

        self.__stopwatch = Stopwatch()
        self.__started = False
        self.__stopped = False
        self.__exhausted = False
        self.__counter_candidates = 0
        self.__counter_tests = 0
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
    def exhausted(self) -> bool:
        """
        Indicates whether or not the space of all possible repairs has been
        exhausted.
        """
        return self.__exhausted

    @property
    def stopped(self) -> bool:
        """
        Indicates whether or not the search has been terminated.
        """
        return self.__stopped

    @property
    def num_test_evals(self) -> int:
        """
        The number of test case evaluations that have been performed during
        this search process.
        """
        return self.__evaluator.num_test_evals

    @property
    def num_candidate_evals(self) -> int:
        """
        The number of candidate patches that have been evaluated over the
        course of this search process.
        """
        return self.__evaluator.num_candidate_evals

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
        The amount nof time that has been spent searching for patches.
        """
        return datetime.timedelta(seconds=self.__stopwatch.duration)

    def __iter__(self) -> Iterator[Candidate]:
        """
        Returns a lazy stream of acceptable patches.

        Raises:
            SearchAlreadyStarted: if the search has already been initiated.
            StopIteration: if the search space or available resources have
                been exhausted.
        """
        if self.__started:
            raise SearchAlreadyStarted
        self.__started = True

        evaluate = self.__evaluator.submit
        reached_time_limit = lambda: \
            self.time_limit and self.time_running > self.time_limit
        reached_candidate_limit = lambda: \
            self.__candidate_limit and self.__counter_candidates > self.__candidate_limit
        # TODO implement test eval limit

        self.__stopwatch.reset()
        self.__stopwatch.start()

        for _ in range(self.__evaluator.num_workers):
            try:
                evaluate(next(self.__candidates))  # type: ignore
            except StopIteration:
                logger.info("all candidate patches have been exhausted")
                self.__exhausted = True
                break

        # as one candidate is evaluated, begin evaluating another
        for candidate, outcome in self.__evaluator.as_completed():
            if outcome.is_repair:
                self.__stopwatch.stop()
                yield candidate
                self.__stopwatch.start()

            # if the search has been stopped, don't evaluate another candidate
            if self.__exhausted:
                continue

            # fetch the next candidate repair
            if reached_time_limit():
                logger.info("time limit has been reached: stopping search.")  # noqa: pycodestyle
                self.__stopped = True
            if reached_candidate_limit():
                logger.info("candidate limit has been reached: stopping search.")  # noqa: pycodestyle
                self.__stopped = True
            try:
                evaluate(next(self.__candidates))  # type: ignore
            except StopIteration:
                logger.info("all candidate patches have been exhausted")
                self.__exhausted = self.__stopped = True

        self.__stopwatch.stop()
