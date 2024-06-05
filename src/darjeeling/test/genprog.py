from __future__ import annotations

__all__ = (
    "GenProgTest",
    "GenProgTestSuite",
    "GenProgTestSuiteConfig",
)

import os
import typing as t
from collections.abc import Sequence
from typing import Any, Optional

import attr

import darjeeling.exceptions as exc
from darjeeling.core import Test, TestOutcome
from darjeeling.test.base import TestSuite
from darjeeling.test.config import TestSuiteConfig

if t.TYPE_CHECKING:
    from ..container import ProgramContainer
    from ..environment import Environment


@attr.s(frozen=True, slots=True, auto_attribs=True)
class GenProgTest(Test):
    name: str


@attr.s(frozen=True, slots=True, auto_attribs=True)
class GenProgTestSuiteConfig(TestSuiteConfig):
    NAME = "genprog"
    workdir: str
    number_failing_tests: int
    number_passing_tests: int
    time_limit_seconds: int

    @classmethod
    def from_dict(cls,
                  d: dict[str, Any],
                  dir_: Optional[str] = None,
                  ) -> TestSuiteConfig:
        # FIXME if no workdir is specified, use source directory specified
        # by program configuration
        workdir = d["workdir"]
        number_failing_tests: int = d["number-of-failing-tests"]
        number_passing_tests: int = d["number-of-passing-tests"]

        if not os.path.isabs(workdir):
            m = "'workdir' property must be an absolute path"
            raise exc.BadConfigurationException(m)

        if "time-limit" not in d:
            time_limit_seconds = 300
        else:
            time_limit_seconds = d["time-limit"]

        return GenProgTestSuiteConfig(workdir=workdir,
                                      number_failing_tests=number_failing_tests,
                                      number_passing_tests=number_passing_tests,
                                      time_limit_seconds=time_limit_seconds)

    def build(self, environment: Environment) -> TestSuite:  # type: ignore[type-arg]
        failing_test_numbers = range(1, self.number_failing_tests + 1)
        passing_test_numbers = range(1, self.number_passing_tests + 1)
        failing_test_names = [f"n{i}" for i in failing_test_numbers]
        passing_test_names = [f"p{i}" for i in passing_test_numbers]
        failing_tests = tuple(GenProgTest(name) for name in failing_test_names)
        passing_tests = tuple(GenProgTest(name) for name in passing_test_names)
        tests = failing_tests + passing_tests
        return GenProgTestSuite(environment=environment,
                                tests=tests,
                                workdir=self.workdir,
                                time_limit_seconds=self.time_limit_seconds)


class GenProgTestSuite(TestSuite[GenProgTest]):
    def __init__(self,
                 environment: Environment,
                 tests: Sequence[GenProgTest],
                 workdir: str,
                 time_limit_seconds: int,
                 ) -> None:
        super().__init__(environment, tests)
        self._workdir = workdir
        self._time_limit_seconds = time_limit_seconds

    def execute(
        self,
        container: ProgramContainer,
        test: GenProgTest,
        *,
        coverage: bool = False,
        environment: t.Optional[t.Mapping[str, str]] = None,
    ) -> TestOutcome:
        command = f"./test.sh {test.name}"
        outcome = container.shell.run(
            command,
            cwd=self._workdir,
            time_limit=self._time_limit_seconds,
            environment=environment,
            text=True,
        )
        successful = outcome.returncode == 0
        return TestOutcome(successful=successful, time_taken=outcome.duration)
