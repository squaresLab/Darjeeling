from typing import Dict
from darjeeling.core import Line


class Localization(object):
    """
    Used to represent a line-level fault localization for a particular
    problem as a mapping from lines to their suspiciousness scores.
    """
    def __init__(self, scores: Dict[Line, float]) -> None:
        self.__scores : Dict[Line, float] = {}


    def score(self, line: Line) -> float:
        """
        Returns the suspiciousness score for a given line. If no suspiciousness
        score is recorded for the given line, then a suspiciousness of zero
        is returned instead.
        """
        return self.__scores.get(line, 0.0)

    __getitem__ = score


    # TODO: restricted_to_files(loc, fns) -> Localization
    # TODO: restricted_to_functions(loc) -> Localization
