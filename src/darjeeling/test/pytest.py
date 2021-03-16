# -*- coding: utf-8 -*-
__all__ = ('PyTestCase', 'PyTestSuite', 'PyTestSuiteConfig')

from typing import Optional, Sequence, Dict, Any
import typing

import attr
import os

from .base import TestSuite
from .config import TestSuiteConfig
from ..core import TestOutcome, Test

if typing.TYPE_CHECKING:
    from ..container import ProgramContainer
    from ..environment import Environment


@attr.s(frozen=True, slots=True, auto_attribs=True)
class PyTestCase(Test):
    name: str


@attr.s(frozen=True, slots=True, auto_attribs=True)
class PyTestSuiteConfig(TestSuiteConfig):
    NAME = 'pytest'
    workdir: str
    test_names: Sequence[str]
    time_limit_seconds: int

    @classmethod
    def from_dict(cls,
                  d: Dict[str, Any],
                  dir_: Optional[str] = None
                  ) -> TestSuiteConfig:
        workdir = d['workdir']
        test_names = tuple(d['tests'])

        if 'time-limit' not in d:
            time_limit_seconds = 300
        else:
            time_limit_seconds = d['time-limit']

        return PyTestSuiteConfig(workdir, test_names, time_limit_seconds)

    def build(self, environment: 'Environment') -> 'TestSuite':
        # TODO automatically discover tests via pytest --setup-only
        tests = tuple(PyTestCase(t) for t in self.test_names)
        return PyTestSuite(environment=environment,
                           tests=tests,
                           workdir=self.workdir,
                           time_limit_seconds=self.time_limit_seconds)


class PyTestSuite(TestSuite[PyTestCase]):
    def __init__(self,
                 environment: 'Environment',
                 tests: Sequence[PyTestCase],
                 workdir: str,
                 time_limit_seconds: int
                 ) -> None:
        super().__init__(environment, tests)
        self._workdir = workdir
        self._time_limit_seconds = time_limit_seconds

    def execute(self,
                container: 'ProgramContainer',
                test: PyTestCase,
                *,
                coverage: bool = False
                ) -> TestOutcome:
        if coverage:
            command = f'coverage run -m pytest {test.name}'
        else:
            command = f'pytest {test.name}'

        outcome = container.shell.run(command,
                                      cwd=self._workdir,
                                      time_limit=self._time_limit_seconds)  # noqa
        successful = outcome.returncode == 0

        output_path = os.path.join(self._workdir, "test_output")
        if container.filesystem.isfile(output_path):
            output = container.filesystem.read(output_path)
        else:
            output = None

        return TestOutcome(test.name, 
                successful=successful, 
                time_taken=outcome.duration,
                output=output)
