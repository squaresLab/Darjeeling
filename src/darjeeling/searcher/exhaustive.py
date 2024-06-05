from __future__ import annotations

__all__ = ("ExhaustiveSearcher",)

import typing
from collections.abc import Iterable, Iterator
from typing import Any, Optional

from loguru import logger

from darjeeling.candidate import Candidate
from darjeeling.exceptions import SearchExhausted
from darjeeling.resources import ResourceUsageTracker
from darjeeling.searcher.base import Searcher
from darjeeling.searcher.config import SearcherConfig
from darjeeling.transformation.base import Transformation

if typing.TYPE_CHECKING:
    from darjeeling.problem import Problem
    from darjeeling.transformation import ProgramTransformations


class ExhaustiveSearcherConfig(SearcherConfig):
    """A configuration for exhaustive search."""
    NAME = "exhaustive"

    def __repr__(self) -> str:
        return "ExhaustiveSearcherConfig()"

    def __str__(self) -> str:
        return repr(self)

    @classmethod
    def from_dict(cls,
                  d: dict[str, Any],
                  dir_: Optional[str] = None,
                  ) -> SearcherConfig:
        return ExhaustiveSearcherConfig()

    def build(self,
              problem: Problem,
              resources: ResourceUsageTracker,
              transformations: ProgramTransformations,
              *,
              threads: int = 1,
              run_redundant_tests: bool = False,
              ) -> Searcher:
        return ExhaustiveSearcher(problem=problem,
                                  resources=resources,
                                  transformations=transformations,
                                  threads=threads,
                                  run_redundant_tests=run_redundant_tests)


class ExhaustiveSearcher(Searcher):
    def __init__(self,
                 problem: Problem,
                 resources: ResourceUsageTracker,
                 transformations: ProgramTransformations,
                 *,
                 threads: int = 1,
                 run_redundant_tests: bool = False,
                 ) -> None:
        # FIXME for now!
        self.__candidates = self.all_single_edit_patches(problem, transformations)
        super().__init__(problem=problem,
                         resources=resources,
                         threads=threads,
                         run_redundant_tests=run_redundant_tests)

    @staticmethod
    def all_single_edit_patches(problem: Problem,
                                transformations: Iterable[Transformation],
                                ) -> Iterator[Candidate]:
        """Returns an iterator over all of the single-edit patches that can be
        composed using a provided source of transformations.
        """
        logger.debug("finding all single-edit patches")
        for t in transformations:
            yield Candidate(problem, [t])
        logger.debug("exhausted all single-edit patches")

    def _generate(self) -> Candidate:
        try:
            logger.debug("generating candidate patch...")
            candidate = next(self.__candidates)
            logger.debug(f"generated candidate patch: {candidate}")
            return candidate
        except StopIteration:
            logger.debug("exhausted all candidate patches")
            raise SearchExhausted

    def run(self) -> Iterator[Candidate]:
        for _ in range(self.num_workers):
            candidate = self._generate()
            self.evaluate(candidate)

        for candidate, outcome in self.as_evaluated():
            if outcome.is_repair:
                yield candidate
            self.evaluate(self._generate())
