# -*- coding: utf-8 -*-
__all__ = ('Reviewer',)

from typing import Any, Dict, Iterable, Iterator, Optional
import typing
from typing import List

from loguru import logger

from .base import Searcher
from .config import SearcherConfig
from ..candidate import Candidate, DiffCandidate, DiffPatch
from ..resources import ResourceUsageTracker
from ..exceptions import SearchExhausted

if typing.TYPE_CHECKING:
    from ..problem import Problem
    from ..transformations import ProgramTransformations


class ReviewerConfig(SearcherConfig):
    """A configuration for reviewing patches."""
    NAME = 'reviewer'

    def __repr__(self) -> str:
        return 'ReviewerConfig()'

    def __str__(self) -> str:
        return repr(self)

    @classmethod
    def from_dict(cls,
                  d: Dict[str, Any],
                  dir_: Optional[str] = None
                  ) -> 'SearcherConfig':
        return ReviewerConfig()

    def build(self,
              problem: 'Problem',
              resources: 'ResourceUsageTracker',
              candidates: 'List[DiffPatch]' = None,
              *,
              transformations: 'Optional[ProgramTransformations]' = None,
              threads: int = 1,
              run_redundant_tests: bool = False
              ) -> Searcher:
        if not candidates:
            candidates = []
        return Reviewer(problem=problem,
                        resources=resources,
                        candidates=candidates,
                        threads=threads)


class Reviewer(Searcher):
    def __init__(self,
                 problem: 'Problem',
                 resources: ResourceUsageTracker,
                 candidates: List[DiffPatch],
                 *,
                 threads: int = 1
                 ) -> None:
        # FIXME for now!
        self.__candidates = self.all_candidates(problem=problem, candidates=candidates)
        super().__init__(problem=problem,
                         resources=resources,
                         threads=threads,
                         run_redundant_tests=False)

    @staticmethod
    def all_candidates(problem: 'Problem',
                       candidates: Iterable[DiffPatch]
                       ) -> Iterator[Candidate]:
        logger.debug(f"Obtaining all patch candidates")
        for c in candidates:
            logger.trace(f"Processing {repr(c)}")
            print(f"Processing {repr(c)}")
            yield DiffCandidate(problem, [], c)
        logger.debug(f"Obtained all patch candidates")

    def _generate(self) -> Candidate:
        try:
            logger.debug('generating candidate patch...')
            candidate = next(self.__candidates)
            logger.debug(f'generated candidate patch: {candidate}')
            return candidate
        except StopIteration:
            logger.debug('exhausted all candidate patches')
            raise SearchExhausted

    def run(self) -> Iterator[Candidate]:
        for _ in range(self.num_workers):
            candidate = self._generate()
            self.evaluate(candidate)

        for candidate, outcome in self.as_evaluated():
            if outcome.is_repair:
                logger.trace(f"{repr(candidate)} PASSED additional evaluation criteria.")
                print(f"{repr(candidate)} PASSED additional evaluation criteria.")
                yield candidate
            else:
                logger.trace(f"{repr(candidate)} FAILED additional evaluation criteria.")
                print(f"{repr(candidate)} FAILED additional evaluation criteria.")
            self.evaluate(self._generate())
