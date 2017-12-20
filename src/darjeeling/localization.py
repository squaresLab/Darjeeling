from typing import Dict
from darjeeling.core import Line


class Localization(object):
    """
    Used to represent a line-level fault localization for a particular
    problem as a mapping from lines to their suspiciousness scores.
    """
    def __init__(self, scores: Dict[Line, float]) -> None:
        self.__scores : Dict[Line, float] = {}


    # TODO: restricted_to_files(loc, fns) -> Localization
    # TODO: restricted_to_functions(loc) -> Localization
