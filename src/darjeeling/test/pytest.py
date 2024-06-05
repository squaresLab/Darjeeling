from __future__ import annotations

__all__ = ("PyTestCase", "PyTestSuite", "PyTestSuiteConfig")

import typing as t
from collections.abc import Sequence
from typing import Any, Optional

import attr

from darjeeling.core import Test, TestOutcome
from darjeeling.test.base import TestSuite
from darjeeling.test.config import TestSuiteConfig

if t.TYPE_CHECKING:
    from darjeeling.container import ProgramContainer
    from darjeeling.environment import Environment


@attr.s(frozen=True, slots=True, auto_attribs=True)
class PyTestCase(Test):
    name: str


@attr.s(frozen=True, slots=True, auto_attribs=True)
class PyTestSuiteConfig(TestSuiteConfig):
    NAME = "pytest"
    workdir: str
    test_names: Sequence[str]
    time_limit_seconds: int

    @classmethod
    def from_dict(cls,
                  d: dict[str, Any],
                  dir_: Optional[str] = None,
                  ) -> TestSuiteConfig:
        workdir = d["workdir"]
        test_names = tuple(d["tests"])

        if "time-limit" not in d:
            time_limit_seconds = 300
        else:
            time_limit_seconds = d["time-limit"]

        return PyTestSuiteConfig(workdir, test_names, time_limit_seconds)

    def build(self, environment: Environment) -> TestSuite:  # type: ignore[type-arg]
        # TODO automatically discover tests via pytest --setup-only
        tests = tuple(PyTestCase(t) for t in self.test_names)
        return PyTestSuite(
            environment=environment,
            tests=tests,
            workdir=self.workdir,
            time_limit_seconds=self.time_limit_seconds,
        )


class PyTestSuite(TestSuite[PyTestCase]):
    def __init__(self,
                 environment: Environment,
                 tests: Sequence[PyTestCase],
                 workdir: str,
                 time_limit_seconds: int,
                 ) -> None:
        super().__init__(environment, tests)
        self._workdir = workdir
        self._time_limit_seconds = time_limit_seconds

    def execute(
        self,
        container: ProgramContainer,
        test: PyTestCase,
        *,
        coverage: bool = False,
        environment: t.Optional[t.Mapping[str, str]] = None,
    ) -> TestOutcome:
        if coverage:
            command = f"coverage run -m pytest {test.name}"
        else:
            command = f"pytest {test.name}"

        outcome = container.shell.run(command,
                                      cwd=self._workdir,
                                      time_limit=self._time_limit_seconds)
        successful = outcome.returncode == 0
        return TestOutcome(successful=successful, time_taken=outcome.duration)
