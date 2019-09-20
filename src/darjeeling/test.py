# -*- coding: utf-8 -*-
from typing import Sequence, Iterator, TypeVar, Dict, Any, Sequence, Generic
import abc

import attr
import bugzoo
from bugzoo import Client as BugZooClient

from .core import TestOutcome, Test
from .config import TestSuiteConfig

T = TypeVar('T', bound=Test)


class TestSuite(Generic[T]):
    def __init__(self, bz: BugZooClient, tests: Sequence[T]) -> None:
        self.__name_to_test = {t.name: t for t in tests}
        self._bugzoo = bz

    def __len__(self) -> int:
        return len(self.__name_to_test)

    def __iter__(self) -> Iterator[Test]:
        yield from self.__name_to_test.values()

    def __getitem__(self, name: str) -> Test:
        return self.__name_to_test[name]

    @abc.abstractmethod
    def execute(self, container: bugzoo.Container, test: T) -> TestOutcome:
        raise NotImplementedError


@attr.s(frozen=True)
class BugZooTestSuiteConfig(TestSuiteConfig):
    NAME = 'bugzoo'

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> TestSuiteConfig:
        return BugZooTestSuiteConfig()


@attr.s(frozen=True, slots=True, auto_attribs=True)
class BugZooTest(Test):
    _test: bugzoo.core.TestCase

    @property
    def name(self) -> str:
        return self._test.name


class BugZooTestSuite(TestSuite[BugZooTest]):
    @classmethod
    def from_bug(cls, bz: bugzoo.Client, bug: bugzoo.Bug) -> 'BugZooTestSuite':
        return BugZooTestSuite(bz, [BugZooTest(t) for t in bug.tests])

    def execute(self,
                container: bugzoo.Container,
                test: BugZooTest
                ) -> TestOutcome:
        bz = self._bugzoo
        bz_outcome = bz.containers.test(container, test._test)
        return TestOutcome(bz_outcome.passed, bz_outcome.duration)
