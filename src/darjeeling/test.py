# -*- coding: utf-8 -*-
from typing import Sequence, Iterator, TypeVar
from abc import abstractmethod

import attr
import bugzoo

from .core import TestOutcome, TestSuite


@attr.s(frozen=True)
class BugZooTest:
    _test: bugzoo.core.TestCase = attr.ib()

    @property
    def name(self) -> str:
        return self._test.name


class BugZooTestSuite(TestSuite):
    @staticmethod
    def from_bug(bz: bugzoo.Client, bug: bugzoo.Bug) -> 'BugZooTestSuite':
        return BugZooTestSuite(bz, [BugZooTest(t) for t in bug.tests])

    def execute(self,
                container: bugzoo.Container,
                test: bugzoo.core.TestCase
                ) -> TestOutcome:
        bz = self._bugzoo
        bz_outcome = bz.containers.test(container, test)
        return TestOutcome(bz_outcome.passed, bz_outcome.duration)
