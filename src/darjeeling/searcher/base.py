# -*- coding: utf-8 -*-
__all__ = ('Searcher',)

from typing import (Iterable, Iterator, Optional, List, Tuple, Any, Dict,
                    Type, TypeVar, Generic, Union, ClassVar, Set)
from typing_extensions import final
from mypy_extensions import NoReturn
import abc
import logging
import datetime
import threading
import inspect
import time
import signal

import bugzoo

from ..events import DarjeelingEventProducer, DarjeelingEventHandler
from ..core import FileLine
from ..config import SearcherConfig
from ..candidate import Candidate
from ..problem import Problem
from ..outcome import OutcomeManager, CandidateOutcome
from ..transformation import Transformation
from ..evaluator import Evaluator, Evaluation
from ..exceptions import BuildFailure, \
    SearchAlreadyStarted, \
    SearchExhausted, \
    TimeLimitReached, \
    CandidateLimitReached, \
    BadConfigurationException
from ..util import Stopwatch, dynamically_registered

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)

T = TypeVar('T', bound=SearcherConfig)


@dynamically_registered('CONFIG',
                        lookup='_searcher_for_config_type',
                        iterator=None)
class Searcher(Generic[T], DarjeelingEventProducer, abc.ABC):
    CONFIG: ClassVar[Type[T]]

    @staticmethod
    def _searcher_for_config_type(type_cfg: Type[SearcherConfig]
                                 ) -> Type['Searcher']:
        """Retrieves associated searcher for a given configuration class."""
        ...

    @classmethod
    @abc.abstractmethod
    def from_config(cls,
                    cfg: T,
                    problem: Problem,
                    tx: List[Transformation],
                    *,
                    threads: int = 1,
                    candidate_limit: Optional[int] = None,
                    time_limit: Optional[datetime.timedelta] = None
                    ) -> 'Searcher':
        type_searcher = Searcher._searcher_for_config_type(cfg.__class__)
        return type_searcher.from_config(cfg, problem, tx,
                                         threads=threads,
                                         candidate_limit=candidate_limit,
                                         time_limit=time_limit)

    def __init__(self,
                 bugzoo: bugzoo.BugZoo,
                 problem: Problem,
                 *,
                 threads: int = 1,
                 time_limit: Optional[datetime.timedelta] = None,
                 candidate_limit: Optional[int] = None,
                 terminate_early: bool = True,
                 test_sample_size: Optional[Union[int, float]] = None
                 ) -> None:
        """
        Constructs a new searcher.

        Parameters:
            bugzoo: a connection to the BugZoo server that should be used to
                evaluate candidate patches.
            problem: a description of the problem.
            threads: the number of threads that should be made available to
                the search process.
            time_limit: an optional limit on the amount of time given to the
                searcher.
            candidate_limit: an optional limit on the number of candidate
                patches that may be generated.
        """
        logger.debug("constructing searcher")
        super().__init__()
        assert time_limit is None or time_limit > datetime.timedelta(), \
            "if specified, time limit should be greater than zero."

        self.__bugzoo = bugzoo
        self.__problem = problem
        self.__time_limit = time_limit
        self.__candidate_limit = candidate_limit
        self.__outcomes = OutcomeManager()
        self.__evaluator = Evaluator(bugzoo,
                                     problem,
                                     num_workers=threads,
                                     terminate_early=terminate_early,
                                     outcomes=self.__outcomes,
                                     sample_size=test_sample_size)

        self.__stopwatch = Stopwatch()
        self.__started = False
        self.__stopped = False
        self.__exhausted = False
        self.__counter_candidates = 0
        self.__counter_tests = 0
        # FIXME this isn't being maintained
        self.__history = []  # type: List[Candidate]
        logger.debug("constructed searcher")

    def attach_handler(self, handler: DarjeelingEventHandler) -> None:
        super().attach_handler(handler)
        self.__evaluator.attach_handler(handler)

    def remove_handler(self, handler: DarjeelingEventHandler) -> None:
        super().remove_handler(handler)
        self.__evaluator.remove_handler(handler)

    @property
    def num_workers(self) -> int:
        return self.__evaluator.num_workers

    @property
    def problem(self) -> Problem:
        """A description of the problem being solved."""
        return self.__problem

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
    def candidate_limit(self) -> Optional[int]:
        return self.__candidate_limit

    @property
    def time_running(self) -> datetime.timedelta:
        """
        The amount of time that has been spent searching for patches.
        """
        return datetime.timedelta(seconds=self.__stopwatch.duration)

    @abc.abstractmethod
    def run(self) -> Iterator[Candidate]:
        ...

    def evaluate(self, candidate: Candidate) -> None:
        if self.time_limit and self.time_running > self.time_limit:
            raise TimeLimitReached
        if self.candidate_limit and self.num_candidate_evals > self.candidate_limit:
            raise CandidateLimitReached
        # FIXME test limit
        self.__evaluator.submit(candidate)

    def evaluate_all(self,
                     candidates: List[Candidate],
                     results: Optional[Dict[Candidate, CandidateOutcome]] = None
                     ) -> Iterator[Candidate]:
        """
        Evaluates all given candidate patches and blocks until all have been
        evaluated (or the search has been terminated).

        Parameters:
            candidates: a list of candidate patches that should be evaluated.
            results: a dictionary to which the results of each candidate
                patch evaluation should be written.

        Returns:
            an iterator over the subset of candidates that are acceptable
            repairs.
        """
        if results is None:
            results = {}

        # FIXME handle duplicates!
        size = len(candidates)
        i = 0
        num_evaluated = 0
        for i in range(min(size, self.__evaluator.num_workers)):
            self.evaluate(candidates[i])
        i = min(size, self.__evaluator.num_workers)
        for candidate, outcome in self.as_evaluated():
            results[candidate] = outcome
            num_evaluated += 1
            if outcome.is_repair:
                yield candidate
            if i < size:
                self.evaluate(candidates[i])
                i += 1

    def as_evaluated(self) -> Iterator[Evaluation]:
        yield from self.__evaluator.as_completed()

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

        self.__stopwatch.reset()
        self.__stopwatch.start()

        try:
            for repair in self.run():
                self.__stopwatch.stop()
                # TODO REPORT THE REPAIR?
                yield repair
                self.__stopwatch.start()
        except SearchExhausted:
            logger.info("all candidate patches have been exhausted")
        # FIXME this one is trickier -- needs to be enforced before the job is started
        except TimeLimitReached:
            logger.info("time limit has been reached: stopping search.")
        except CandidateLimitReached:
            logger.info("candidate limit has been reached: stopping search.")

        # wait for remaining evaluations
        for candidate, outcome in self.as_evaluated():
            if outcome.is_repair:
                self.__stopwatch.stop()
                yield candidate
                self.__stopwatch.start()

        self.__stopwatch.stop()

    def close(self) -> None:
        logger.info("waiting for pending evaluations to complete.")
        for candidate, outcome in self.as_evaluated():
            pass
        logger.info("finished waiting for pending evaluations to complete.")
