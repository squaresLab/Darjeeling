from typing import List, Optional, Tuple
from datetime import timedelta

import bugzoo
from bugzoo.localization import SuspiciousnessMetric

from darjeeling.problem import Problem
from darjeeling.candidate import Candidate
from darjeeling.search import RandomSearch


class RepairReport(object):
    def __init__(self):
        self.__num_candidate_evals = None
        self.__num_test_evals = None
        self.__duration = None

    @property
    def num_candidate_evals(self) -> int:
        """
        Number of candidate evaluations performed during the search.
        """
        return self.__num_candidate_evals

    @property
    def num_test_evals(self) -> int:
        """
        Number of test-case evaluations performed during the search.
        """
        return self.__num_test_evals


    @property
    def duration(self) -> timedelta:
        """
        The wall-clock duration of the search process.
        """
        return self.__duration


def repair(bugzoo: bugzoo.BugZoo,
           problem: Problem,
           metric: SuspiciousnessMetric,
           seed: Optional[int] = None,
           threads: Optional[int] = 1,
           terminate_early: bool = True
           ) -> Tuple[List[Candidate], RepairReport]:
    """
    Attempts to repair a given program.

    Returns:
        A tuple of the form `(patches, report)`, where `patches` is a list
        of all the candidate patches discovered during the search, and
        `report` contains a summary of the search process.
    """
    searcher = RandomSearch(bugzoo, problem, threads, terminate_early)
    searcher.run(seed)
