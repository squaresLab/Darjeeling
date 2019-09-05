# -*- coding: utf-8 -*-
__all__ = ('Config',)

from typing import Optional

import attr


@attr.s
class Config:
    """A configuration for Darjeeling.

    Attributes
    ----------
    num_threads: int
        The number of threads over which the search should be distributed.
    limit_candidates: int, optional
        An optional limit on the number of candidate patches that may be
        considered by the search.
    limit_time_minutes: int, optional
        An optional limit on the number of minutes that may be spent
        searching for an acceptable patch.
    """
    num_threads: int = attr.ib(default=1)
    limit_candidates: Optional[int] = attr.ib(default=None)
    limit_time_minutes: Optional[float] = attr.ib(default=None)
