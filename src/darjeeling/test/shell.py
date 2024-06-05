from __future__ import annotations

__all__ = (
    "ShellTest",
    "ShellTestSuite",
    "ShellTestSuiteConfig",
)

import os
import typing as t

import attr
from loguru import logger

from .. import exceptions as exc
from ..core import Test, TestOutcome
from .base import TestSuite
from .config import TestSuiteConfig

if t.TYPE_CHECKING:
    from ..container import ProgramContainer
    from ..environment import Environment


@attr.s(frozen=True, slots=True, auto_attribs=True)
class ShellTest(Test):
    name: str
    command: str


@attr.s(frozen=True, slots=True, auto_attribs=True)
class ShellTestSuiteConfig(TestSuiteConfig):
    NAME = "shell"
    workdir: str
    test_commands: t.Sequence[str]
    time_limit_seconds: int

    @classmethod
    def from_dict(
        cls,
        d: dict[str, t.Any],
        dir_: t.Optional[str] = None,
    ) -> TestSuiteConfig:
        workdir = d["workdir"]
        test_commands = d["tests"]

        if not os.path.isabs(workdir):
            m = "'workdir' property must be an absolute path"
            raise exc.BadConfigurationException(m)

        if not isinstance(test_commands, list):
            m = "expected 'tests' property to be a list of strings"
            raise exc.BadConfigurationException(m)

        if "time-limit" not in d:
            time_limit_seconds = 300
        else:
            time_limit_seconds = d["time-limit"]

        return ShellTestSuiteConfig(
            workdir=workdir,
            test_commands=tuple(test_commands),
            time_limit_seconds=time_limit_seconds,
        )

    def build(self, environment: Environment) -> TestSuite:  # type: ignore[type-arg]
        return ShellTestSuite.build(
            environment=environment,
            workdir=self.workdir,
            test_commands=self.test_commands,
            time_limit_seconds=self.time_limit_seconds,
        )


class ShellTestSuite(TestSuite[ShellTest]):
    @classmethod
    def build(
        cls,
        environment: Environment,
        workdir: str,
        test_commands: t.Sequence[str],
        time_limit_seconds: int = 300,
    ) -> ShellTestSuite:
        tests = tuple(
            ShellTest(f"t{n}", command)
            for (n, command) in enumerate(test_commands)
        )
        return ShellTestSuite(
            environment=environment,
            tests=tests,
            workdir=workdir,
            time_limit_seconds=time_limit_seconds,
        )

    def __init__(
        self,
        environment: Environment,
        tests: t.Sequence[ShellTest],
        workdir: str,
        time_limit_seconds: int,
    ) -> None:
        super().__init__(environment, tests)
        self._workdir = workdir
        self._time_limit_seconds = time_limit_seconds

    def execute(
        self,
        container: ProgramContainer,
        test: ShellTest,
        *,
        coverage: bool = False,
        environment: t.Optional[t.Mapping[str, str]] = None,
    ) -> TestOutcome:
        outcome = container.shell.run(
            test.command,
            cwd=self._workdir,
            time_limit=self._time_limit_seconds,
            environment=environment,
            text=True,
        )
        logger.trace(f"shell test outcome: {outcome}")
        successful = outcome.returncode == 0
        return TestOutcome(
            successful=successful,
            time_taken=outcome.duration,
        )
