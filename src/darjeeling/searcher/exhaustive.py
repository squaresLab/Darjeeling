from typing import Iterable, Optional, Iterator
import datetime

from bugzoo import Client as BugZooClient

from .base import Searcher
from ..candidate import Candidate
from ..problem import Problem
from ..exceptions import SearchExhausted


class ExhaustiveSearcher(Searcher):
    def __init__(self,
                 bugzoo: BugZooClient,
                 problem: Problem,
                 candidates: Iterable[Candidate],
                 *,
                 threads: int = 1,
                 time_limit: Optional[datetime.timedelta] = None,
                 candidate_limit: Optional[int] = None
                 ) -> None:
        self.__candidates = candidates
        super().__init__(bugzoo=bugzoo,
                         problem=problem,
                         threads=threads,
                         time_limit=time_limit,
                         candidate_limit=candidate_limit)

    def _generate(self) -> Candidate:
        try:
            return next(self.__candidates)
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
