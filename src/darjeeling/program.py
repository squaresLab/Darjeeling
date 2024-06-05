from __future__ import annotations

__all__ = (
    "ProgramDescription",
    "ProgramDescriptionConfig",
)

import contextlib
import typing as t
from collections.abc import Iterator, Mapping
from typing import Any, NoReturn, Optional

import attr
from bugzoo import Bug as Snapshot
from bugzoo.core.patch import Patch
from loguru import logger

import darjeeling.exceptions as exc
from darjeeling.build_instructions import BuildInstructions
from darjeeling.container import ProgramContainer
from darjeeling.core import Language, Test, TestOutcome
from darjeeling.exceptions import BuildFailure, FailedToApplyPatch
from darjeeling.test import TestSuite, TestSuiteConfig

if t.TYPE_CHECKING:
    from darjeeling.environment import Environment


@attr.s(frozen=True, slots=True, auto_attribs=True)
class ProgramDescriptionConfig:
    image: str
    language: Language
    build_instructions: BuildInstructions
    build_instructions_for_coverage: BuildInstructions
    tests: TestSuiteConfig
    source_directory: str
    snapshot: Optional[Snapshot]

    @staticmethod
    def from_dict(dict_: Mapping[str, Any],
                  dir_: Optional[str] = None,
                  ) -> ProgramDescriptionConfig:
        def err(message: str) -> NoReturn:
            raise exc.BadConfigurationException(message)

        # image
        if "image" not in dict_:
            err("'image' property is missing from 'program' section")
        if not isinstance(dict_["image"], str):
            err("'image' property should be a string")
        image: str = dict_["image"]

        # source directory
        if "source-directory" not in dict_:
            err("'source-directory' property is missing from 'program' section")
        if not isinstance(dict_["source-directory"], str):
            err("'source-directory' property should be a string")
        source_directory: str = dict_["source-directory"]

        # language
        if "language" not in dict_:
            err("'language' property is missing from 'program' section")
        if not isinstance(dict_["language"], str):
            err("'language' property should be a string")
        try:
            language: Language = Language.find(dict_["language"])
        except exc.LanguageNotSupported:
            supported = ", ".join([lang.value for lang in Language])
            supported = f"(supported languages: {supported})"
            err(f"unsupported language [{dict_['language']}]. {supported}")

        # test suite
        if "tests" not in dict_:
            err("'tests' section is missing from 'program' section")
        if not isinstance(dict_["tests"], dict):
            err("'tests' section should be an object")
        tests = TestSuiteConfig.from_dict(dict_.get("tests", {}), dir_)

        # build instructions
        if "build-instructions" not in dict_:
            err("'build-instructions' section is missing from 'program' section")
        if not isinstance(dict_["build-instructions"], dict):
            err("'build-instructions' section should be an object")
        build_instructions, build_instructions_for_coverage = \
            BuildInstructions.from_dict(dict_["build-instructions"],
                                        source_directory=source_directory)

        return ProgramDescriptionConfig(image=image,
                                        language=language,
                                        build_instructions=build_instructions,
                                        build_instructions_for_coverage=build_instructions_for_coverage,
                                        tests=tests,
                                        snapshot=None,
                                        source_directory=source_directory)

    def build(self, environment: Environment) -> ProgramDescription:
        tests = self.tests.build(environment)
        return ProgramDescription(environment=environment,
                                  image=self.image,
                                  language=self.language,
                                  snapshot=self.snapshot,
                                  build_instructions=self.build_instructions,
                                  build_instructions_for_coverage=self.build_instructions_for_coverage,
                                  tests=tests,
                                  source_directory=self.source_directory)


@attr.s(frozen=True, slots=True, auto_attribs=True)
class ProgramDescription:
    """Provides a description of a program.

    Attributes
    ----------
    image: str
        The name of the Docker image for this progrma.
    language: Language
        The language in which the program is written.
    build_instructions: BuildInstructions
        Executable instructions for building the program.
    build_instructions_for_coverage: BuildInstructions
        Executable instructions for building the program with coverage
        instrumentation.
    snapshot:
        The BugZoo snapshot for this program.
    tests: TestSuite
        The test suite for this program.
    source_directory: str
        The absolute path to the source directory for this program inside
        its associated Docker image.
    """
    _environment: Environment
    image: str
    language: Language
    snapshot: Optional[Snapshot]
    build_instructions: BuildInstructions
    build_instructions_for_coverage: BuildInstructions
    tests: TestSuite  # type: ignore[type-arg]
    source_directory: str

    def execute(
        self,
        container: ProgramContainer,
        test: Test,
        *,
        coverage: bool = False,
        environment: t.Optional[t.Mapping[str, str]] = None,
    ) -> TestOutcome:
        """Executes a given test in a container.

        Parameters
        ----------
        container: ProgramContainer
            The container for the program under test.
        test: Test
            The test case that should be executed.
        coverage: bool
            If :code:`True`, the test harness will be instructed to run the
            test in coverage collection mode. If no such mode is supported,
            the test will be run as usual.
        environment: Mapping[str, str], optional
            An optional set of environment variables that should be used when
            executing the test.

        Returns
        -------
        TestOutcome
            A concise summary of the test execution.
        """
        return self.tests.execute(
            container,
            test,
            coverage=coverage,
            environment=environment,
        )

    def provision(self) -> ProgramContainer:
        """Provisions a container for this program."""
        return ProgramContainer.for_program(self._environment, self)

    @contextlib.contextmanager
    def build(self, patch: Patch) -> Iterator[ProgramContainer]:
        """Builds a container for a given patch.

        Yields
        ------
        Container
            A ready-to-use container that contains a built version of the
            patched source code.

        Raises
        ------
        BuildFailure
            If the program failed to build.
        """
        with self.provision() as container:
            try:
                container.patch(patch)
            except FailedToApplyPatch:
                logger.debug(f"failed to apply patch: {patch}")
                raise BuildFailure

            try:
                self.build_instructions.execute(container)
            except exc.BuildStepFailed:
                raise BuildFailure

            yield container
