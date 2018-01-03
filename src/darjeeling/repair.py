from datetime import timedelta
from typing import List, Optional
from bugzoo import BugZoo
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


def repair(problem: Problem,
           metric: SuspiciousnessMetric,
           threads: Optional[int] = 1,
           terminate_early: bool = True
           ) -> RepairReport:
    searcher = RandomSearch(problem, threads, terminate_early)
    searcher.run(terminate_early)
