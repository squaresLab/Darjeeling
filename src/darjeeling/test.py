# -*- coding: utf-8 -*-
from typing import Sequence, Iterator, TypeVar, Dict, Any
from abc import abstractmethod

import attr
import bugzoo

from .core import TestOutcome, TestSuite, Test
from .config import TestSuiteConfig


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
    @staticmethod
    def from_bug(bz: bugzoo.Client, bug: bugzoo.Bug) -> 'BugZooTestSuite':
        return BugZooTestSuite(bz, [BugZooTest(t) for t in bug.tests])

    def execute(self,
                container: bugzoo.Container,
                test: BugZooTest
                ) -> TestOutcome:
        bz = self._bugzoo
        bz_outcome = bz.containers.test(container, test._test)
        return TestOutcome(bz_outcome.passed, bz_outcome.duration)
