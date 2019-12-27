# -*- coding: utf-8 -*-
__all__ = ('BugZooTest', 'BugZooTestSuite', 'BugZooTestSuiteConfig')

from typing import Dict, Any, Optional

import attr
import bugzoo
from bugzoo import Bug

from .base import TestSuite, TestSuiteConfig
from ..core import TestOutcome, Test
from ..config import TestSuiteConfig
from ..container import ProgramContainer
from ..environment import Environment


class BugZooTestSuiteConfig(TestSuiteConfig):
    NAME = 'bugzoo'

    @classmethod
    def from_dict(cls,
                  d: Dict[str, Any],
                  dir_: Optional[str] = None
                  ) -> TestSuiteConfig:
        return BugZooTestSuiteConfig()

    def build(self, environment: Environment, bug: Bug) -> 'TestSuite':
        tests = tuple(BugZooTest(t) for t in bug.tests)
        return BugZooTestSuite(environment, tests)


@attr.s(frozen=True, slots=True, auto_attribs=True)
class BugZooTest(Test):
    _test: bugzoo.core.TestCase

    @property
    def name(self) -> str:
        return self._test.name


class BugZooTestSuite(TestSuite[BugZooTest]):
    def execute(self,
                container: ProgramContainer,
                test: BugZooTest,
                *,
                coverage: bool = False
                ) -> TestOutcome:
        bz = self._environment.bugzoo
        bz_outcome = bz.containers.test(container._bugzoo, test._test)
        return TestOutcome(bz_outcome.passed, bz_outcome.duration)
