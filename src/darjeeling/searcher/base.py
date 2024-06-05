__all__ = ("Searcher",)

import abc
import typing
from collections.abc import Iterator
from typing import Optional, Union

from loguru import logger

from darjeeling.candidate import Candidate
from darjeeling.environment import Environment
from darjeeling.evaluator import Evaluation, Evaluator
from darjeeling.events.handler import DarjeelingEventHandler
from darjeeling.events.producer import DarjeelingEventProducer
from darjeeling.exceptions import (
    CandidateLimitReached,
    SearchAlreadyStarted,
    SearchExhausted,
    TimeLimitReached,
)
from darjeeling.outcome import CandidateOutcome
from darjeeling.resources import ResourceUsageTracker

if typing.TYPE_CHECKING:
    from darjeeling.problem import Problem


class Searcher(DarjeelingEventProducer, abc.ABC):
    def __init__(self,
                 problem: "Problem",
                 resources: ResourceUsageTracker,
                 *,
                 threads: int = 1,
                 terminate_early: bool = True,
                 test_sample_size: Optional[Union[int, float]] = None,
                 run_redundant_tests: bool = True,
                 ) -> None:
        """Constructs a new searcher.

        Parameters
        ----------
        problem: Problem
            a description of the problem.
        resources: ResourceUsageTracker
            tracks and monitors the resources used by the search.
        threads: int
            the number of threads that should be made available to
            the search process.
        run_redundant_tests: bool
            Specifies if redundant tests should be run. Tests are deemed
            redundant if a candidate patch does not change lines that the
            test uses. Lines used are determined by test coverage.
        """
        logger.debug("constructing searcher")
        super().__init__()

        self.__resources = resources
        self.__problem = problem
        self.__evaluator = Evaluator(problem=problem,
                                     resources=resources,
                                     num_workers=threads,
                                     terminate_early=terminate_early,
                                     sample_size=test_sample_size,
                                     run_redundant_tests=run_redundant_tests)

        self.__started = False
        self.__stopped = False
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
    def problem(self) -> "Problem":
        """A description of the problem being solved."""
        return self.__problem

    @property
    def environment(self) -> Environment:
        return self.problem.environment

    @property
    def stopped(self) -> bool:
        """Indicates whether or not the search has been terminated."""
        return self.__stopped

    @abc.abstractmethod
    def run(self) -> Iterator[Candidate]:
        ...

    def evaluate(self, candidate: Candidate) -> None:
        self.__resources.check_limits()
        self.__evaluator.submit(candidate)

    def evaluate_all(self,
                     candidates: list[Candidate],
                     results: Optional[dict[Candidate, CandidateOutcome]] = None,
                     ) -> Iterator[Candidate]:
        """Evaluates all given candidate patches and blocks until all have been
        evaluated (or the search has been terminated).

        Parameters
        ----------
            candidates: a list of candidate patches that should be evaluated.
            results: a dictionary to which the results of each candidate
                patch evaluation should be written.

        Returns
        -------
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
        """Returns a lazy stream of acceptable patches.

        Raises
        ------
            SearchAlreadyStarted: if the search has already been initiated.
            StopIteration: if the search space or available resources have
                been exhausted.
        """
        stopwatch = self.__resources.wall_clock
        if self.__started:
            raise SearchAlreadyStarted
        self.__started = True

        stopwatch.reset()
        stopwatch.start()

        try:
            for repair in self.run():
                stopwatch.stop()
                yield repair
                stopwatch.start()
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
                stopwatch.stop()
                yield candidate
                stopwatch.start()

        stopwatch.stop()

    def close(self) -> None:
        logger.info("waiting for pending evaluations to complete.")
        for candidate, outcome in self.as_evaluated():
            pass
        logger.info("finished waiting for pending evaluations to complete.")
