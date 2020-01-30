# -*- coding: utf-8 -*-
"""
This module is used to provide a variety of schemes for test
ordering/prioritisation that all implement a common interface.
"""
import abc
from typing import Set, Sequence
from typing_extensions import final


class TestOrdering(abc.ABC):
    @final
    def __call__(self, tests: Set[Test]) -> Sequence[Test]:
        return self.order(tests)

    @abc.abstractmethod
    def order(self, tests: Set[Test]) -> Sequence[Test]:
        return


@attr.s(frozen=True, auto_attribs=True)
class StaticTestOrdering(TestOrdering):
    _order: Sequence[Test]

    @classmethod
    def for_problem(problem: Problem) -> 'StaticTestOrdering':
        return

    def order(self, tests: Set[Test]) -> Sequence[Test]:
        ordered: Sequence[Test] = []
        for test in self._order:
            ordered.append(test)
        return ordered


# likelihood of failure
# execution time
