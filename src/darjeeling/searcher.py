from typing import Iterable, Iterator
from timeit import default_timer as timer
import datetime

from .candidate import Candidate
from .problem import Problem


class Searcher(object):
    def __init__(self,
                 problem: Problem,
                 candidates: Iterable[Candidate],
                 *,
                 threads: int = 1,
                 time_limit: Optional[timedelta] = None
                 ) -> None:
        """
        Constructs a new searcher for a given source of candidate patches.

        Parameters:
            problem: a description of the problem.
            candidates: a source of candidate patches.
            threads: the number of threads that should be made available to
                the search process.
            time_limit: an optional limit on the amount of time given to the
                searcher.
        """
        assert time_limit is None or time_limit > 0, \
            "if specified, time limit should be greater than zero."

        self.__problem = problem
        self.__candidates = candidates
        self.__time_running = datetime.timedelta()
        self.__time_limit = time_limita
        self.__num_threads = threads

        # records the time at which the current iteration begun
        self.__time_iteration_begun = None

    @property
    def exhausted(self) -> bool:
        """
        Indicates whether or not the resources available to this searcher have
        been exhausted.
        """
        if self.__time_limit is None:
            return False

        return self.time_running > self.time_limit

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
        duration_iteration = timer() - self.__time_start_iteration
        return self.__time_running + duration_iteration

    def __iter__(self) -> Iterator[Candidate]:
        return self

    def __next__(self) -> Candidate:
        """
        Searches for the next acceptable patch.

        Returns:
            the next patch that passes all tests.

        Raises:
            StopIteration: if the search space or available resources have
                been exhausted.
        """
        self.__time_iteration_begun = timer()
        try:
            raise NotImplementedError

        # ensure all the patch evaluators are killed
        finally:
            duration_iteration = timer() - self.__time_start_iteration
            self.__time_running += duration_iteration
