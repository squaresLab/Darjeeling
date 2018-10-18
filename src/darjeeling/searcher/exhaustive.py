from typing import Iterable, Optional, Iterator, Dict, Any, List
import datetime

from bugzoo import Client as BugZooClient

from .base import Searcher
from ..candidate import Candidate, all_single_edit_patches
from ..problem import Problem
from ..transformation import Transformation
from ..exceptions import SearchExhausted


class ExhaustiveSearcher(Searcher):
    @staticmethod
    def from_dict(d: Dict[str, Any],
                  problem: Problem,
                  transformations: List[Transformation],
                  *,
                  threads: int = 1,
                  candidate_limit: Optional[int] = None,
                  time_limit: Optional[datetime.timedelta] = None
                  ) -> 'ExhaustiveSearcher':
        return ExhaustiveSearcher(problem.bugzoo,
                                  problem,
                                  transformations,
                                  threads=threads,
                                  candidate_limit=candidate_limit,
                                  time_limit=time_limit)

    def __init__(self,
                 bugzoo: BugZooClient,
                 problem: Problem,
                 transformations: List[Transformation],
                 *,
                 threads: int = 1,
                 time_limit: Optional[datetime.timedelta] = None,
                 candidate_limit: Optional[int] = None
                 ) -> None:
        # FIXME for now!
        self.__candidates = all_single_edit_patches(transformations)
        super().__init__(bugzoo=bugzoo,
                         problem=problem,
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
