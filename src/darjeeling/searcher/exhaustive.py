# -*- coding: utf-8 -*-
__all__ = ('ExhaustiveSearcher',)

from typing import Iterable, Optional, Iterator, Dict, Any, List
import datetime
import typing

from .base import Searcher
from .config import SearcherConfig
from ..candidate import Candidate, all_single_edit_patches
from ..environment import Environment
from ..transformation import Transformation
from ..exceptions import SearchExhausted

if typing.TYPE_CHECKING:
    from ..problem import Problem


class ExhaustiveSearcherConfig(SearcherConfig):
    """A configuration for exhaustive search."""
    NAME = 'exhaustive'

    def __repr__(self) -> str:
        return 'ExhaustiveSearcherConfig()'

    def __str__(self) -> str:
        return repr(self)

    @classmethod
    def from_dict(cls,
                  d: Dict[str, Any],
                  dir_: Optional[str] = None
                  ) -> 'SearcherConfig':
        return ExhaustiveSearcherConfig()

    def build(self,
              problem: 'Problem',
              transformations: List[Transformation],
              *,
              threads: int = 1,
              candidate_limit: Optional[int] = None,
              time_limit: Optional[datetime.timedelta] = None
              ) -> Searcher:
        return ExhaustiveSearcher(problem,
                                  transformations,
                                  threads=threads,
                                  candidate_limit=candidate_limit,
                                  time_limit=time_limit)


class ExhaustiveSearcher(Searcher):
    CONFIG = ExhaustiveSearcherConfig

    def __init__(self,
                 problem: 'Problem',
                 transformations: List[Transformation],
                 *,
                 threads: int = 1,
                 time_limit: Optional[datetime.timedelta] = None,
                 candidate_limit: Optional[int] = None
                 ) -> None:
        # FIXME for now!
        self.__candidates = all_single_edit_patches(transformations)
        super().__init__(problem=problem,
                         threads=threads,
                         time_limit=time_limit,
                         candidate_limit=candidate_limit)

    def _generate(self) -> Candidate:
        try:
            return next(self.__candidates)  # type: ignore
        except StopIteration:
            raise SearchExhausted

    def run(self) -> Iterator[Candidate]:
        for _ in range(self.num_workers):
            candidate = self._generate()
            self.evaluate(candidate)

        for candidate, outcome in self.as_evaluated():
            if outcome.is_repair:
                yield candidate
            self.evaluate(self._generate())
