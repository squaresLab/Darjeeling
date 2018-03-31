from typing import Iterable, Iterator
import datetime

from .candidate import Candidate
from .problem import Problem


class Searcher(object):
    def __init__(self,
                 problem: Problem,
                 candidates: Iterable[Candidate]
                 ) -> None:
        """
        Constructs a new searcher for a given source of candidate patches.

        Parameters:
            problem: a description of the problem.
            candidates: a source of candidate patches.
        """
        self.__problem = problem
        self.__candidates = candidates
        self.__time_running = datetime.timedelta()

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
        # TODO this is where the magic happens
        raise NotImplementedError
