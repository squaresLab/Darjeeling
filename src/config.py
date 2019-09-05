# -*- coding: utf-8 -*-
__all__ = ('Config',)

from typing import Optional

import attr


@attr.s
class Config:
    """A configuration for Darjeeling.

    Attributes
    ----------
    seed: int
        The seed that should be used by the random number generator.
    terminate_early: bool
        Specifies whether or not the search should terminate upon
        discovering an acceptable patch.
    num_threads: int
        The number of threads over which the search should be distributed.
    limit_candidates: int, optional
        An optional limit on the number of candidate patches that may be
        considered by the search.
    limit_time_minutes: int, optional
        An optional limit on the number of minutes that may be spent
        searching for an acceptable patch.
    """
    seed: int = attr.ib()  # FIXME use factory to generate default
    terminate_early: bool = attr.ib(default=True)
    num_threads: int = attr.ib(default=1)
    limit_candidates: Optional[int] = attr.ib(default=None)
    limit_time_minutes: Optional[float] = attr.ib(default=None)
