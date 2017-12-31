from datetime import timedelta
from typing import List, Optional
from bugzoo import BugZoo
from bugzoo.localization import SuspiciousnessMetric
from darjeeling.problem import Problem
from darjeeling.candidate import Candidate


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


def evaluate(problem: Problem, candidate: Candidate) -> bool:
    """
    Determines whether a given candidate patch fixes the bug.
    Returns True if the bug is fixed, or False if it is not.
    """
    print("Evaluating: {}".format(candidate))
    container = problem.bug.provision()
    patch = candidate.diff(problem)
    try:
        container.patch(patch)

        # for now, execute all tests in no particular order
        for test in problem.tests:
            outcome = container.execute(test)
            if not outcome.passed:
                return False

        return True
    finally:
        container.destroy()


def repair(problem: Problem,
           metric: SuspiciousnessMetric,
           ) -> RepairReport:
    # connect to the BugZoo daemon
    # - maybe it should be passed a client connection object?
    # TODO: connect to multiple nodes
    bugzoo = BugZoo()

    # generate fault localization
    # localization = Localization.from_spectra(spectra, metric)

    # begin the search!
    print("Beginning search...")

    #
    t = list(problem.transformations)[0]
    candidate = Candidate([t])

    # let's evaluate
    outcome = evaluate(problem, candidate)
    if outcome:
        print("Repair found: {}".format(candidate))
