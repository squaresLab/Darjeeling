from typing import Iterator, List, Sequence
import random

from bugzoo.core.test import TestCase

from .candidate import Candidate
from .transformation import Transformation

Population = List[Individual]


class Strategy(object):
    pass


@attr.ib(frozen=True)
class ExhaustiveStrategy(Strategy):
    pass


@attr.ib(frozen=True)
class RSRepairStrategy(Strategy):
    pass


@attr.ib(frozen=True)
class GreedyStrategy(Strategy):
    pass


class TestSelector(object):
    pass


class CandidateEvaluator(object):
    def evaluate(self,
                 candidate: Candidate,
                 tests: Sequence[Test]) -> None:
        pass
