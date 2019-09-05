# -*- coding: utf-8 -*-
__all__ = ('Config', 'OptimizationsConfig')

from typing import Optional

import attr


@attr.s
class Config:
    """A configuration for Darjeeling.

    Attributes
    ----------
    snapshot: str
        The name of the BugZoo snapshot that should be repaired.
    language: Language
        The language that is used by the program under repair.
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
    snapshot: str = attr.ib()
    language: Language = attr.ib()
    optimizations: OptimizationsConfig = attr.ib(factory=OptimizationsConfig)
    seed: int = attr.ib()  # FIXME use factory to generate default
    terminate_early: bool = attr.ib(default=True)
    num_threads: int = attr.ib(default=1)
    limit_candidates: Optional[int] = attr.ib(default=None)
    limit_time_minutes: Optional[float] = attr.ib(default=None)


@attr.s
class OptimizationsConfig:
    """Specifies which optimizations should be applied during search."""
    use_scope_checking: bool = attr.ib(default=False)
    use_syntax_scope_checking: bool = attr.ib(default=True)
    ignore_dead_code: bool = attr.ib(default=False)
    ignore_equivalent_appends: bool = attr.ib(default=False)
    ignore_untyped_returns: bool = attr.ib(default=False)
    ignore_string_equivalent_snippets: bool = attr.ib(default=False)
    ignore_decls: bool = attr.ib(default=True)
    only_insert_executed_code = attr.ib(default=False)
