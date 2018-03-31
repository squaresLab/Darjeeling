from typing import List, Optional, Tuple
from datetime import timedelta

import bugzoo
from bugzoo.core.fileline import FileLine
from bugzoo.localization import SuspiciousnessMetric

from .problem import Problem
from .candidate import Candidate
from .searcher import Searcher
from .generator import DeletionGenerator, \
                       ReplacementGenerator, \
                       AppendGenerator, \
                       SingleEditPatches, \
                       AllTransformationsAtLine, \
                       SampleByLocalization


__ALL__ = ['RepairReport', 'repair']


class RepairReport(object):
    def __init__(self,
                 num_candidate_evals: int,
                 num_test_evals: int,
                 duration: timedelta):
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
           seed: Optional[int] = None,
           threads: Optional[int] = 1,
           terminate_early: Optional[bool] = True,
           time_limit: Optional[timedelta] = None
           ) -> Tuple[List[Candidate], RepairReport]:
    """
    Attempts to repair a given program.

    Returns:
        A tuple of the form `(patches, report)`, where `patches` is a list
        of all the candidate patches discovered during the search, and
        `report` contains a summary of the search process.
    """
    transformations = \
        SampleByLocalization(problem.localization,
                             problem.snippets,
                             randomize=False)
    candidates = SingleEditPatches(transformations)

    searcher = Searcher(bugzoo,
                        problem,
                        candidates,
                        threads=threads,
                        time_limit=time_limit)
    # FIXME implement terminate_early functionality!
    repairs = list(searcher)
    report = RepairReport(searcher.num_candidate_evals,
                          searcher.num_test_evals,
                          searcher.time_running)
    return (repairs, report)
