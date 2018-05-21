from typing import List, Optional, Tuple, Callable
from datetime import timedelta
import logging

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

logger = logging.getLogger(__name__)


__all__ = ['RepairReport', 'repair']


class RepairReport(object):
    def __init__(self,
                 num_candidate_evals: int,
                 num_test_evals: int,
                 duration: timedelta) -> None:
        self.__num_candidate_evals = num_candidate_evals
        self.__num_test_evals = num_test_evals
        self.__duration = duration

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
           threads: int = 1,
           terminate_early: Optional[bool] = True,
           time_limit: Optional[timedelta] = None,
           logger: Optional[logging.Logger] = None
           ) -> Tuple[List[Candidate], RepairReport]:
    """
    Attempts to repair a given program.

    Returns:
        A tuple of the form `(patches, report)`, where `patches` is a list
        of all the candidate patches discovered during the search, and
        `report` contains a summary of the search process.
    """
    # line = FileLine("ArduCopter/Log.cpp", 577)
    # transformations = \
    #     AllTransformationsAtLine(line, problem.snippets)
    transformations = \
        SampleByLocalization(problem,
                             problem.localization,
                             problem.snippets,
                             randomize=False)
    candidates = SingleEditPatches(transformations)

    searcher = Searcher(bugzoo,
                        problem,
                        candidates,
                        threads=threads,
                        time_limit=time_limit)

    if terminate_early:
        try:
            repairs = [next(searcher)]
        except StopIteration:
            print("stopping iteration")
            repairs = []
    else:
        repairs = list(searcher)

    #for candidate in searcher.outcomes:
    #    outcome = searcher.outcomes[candidate]
    #    if not outcome.build.successful:
    #        print("FAILED TO COMPILE: {}".format(candidate))
    #    else:
    #        try:
    #            failed = next(t for t in outcome.tests if not outcome.tests[t].successful)
    #            print("FAILED TEST ({}): {}".format(failed, candidate))
    #        except StopIteration:
    #            print("SUCCESS: {}".format(candidate))

    report = RepairReport(searcher.num_candidate_evals,
                          searcher.num_test_evals,
                          searcher.time_running)
    return (repairs, report)
