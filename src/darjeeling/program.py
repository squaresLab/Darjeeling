# -*- coding: utf-8 -*-
__all__ = ('ProgramDescription',)

from typing import Iterator
import contextlib
import logging

import attr
from bugzoo import Bug as Snapshot
from bugzoo.core.patch import Patch

from .build_instructions import BuildInstructions
from .core import Test, TestOutcome
from .container import ProgramContainer
from .environment import Environment
from .test import TestSuite, BugZooTestSuite
from .config import Config
from .exceptions import (BadConfigurationException,
                         BuildFailure,
                         FailedToApplyPatch)

logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@attr.s(frozen=True, slots=True, auto_attribs=True)
class ProgramDescription:
    """Provides a description of a program.

    Attributes
    ----------
    image: str
        The name of the Docker image for this progrma.
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
    snapshot: Snapshot
    build_instructions: BuildInstructions
    build_instructions_for_coverage: BuildInstructions
    tests: TestSuite
    source_directory: str

    @staticmethod
    def from_config(environment: Environment,
                    cfg: Config
                    ) -> 'ProgramDescription':
        """Loads a program from a given configuration.

        Raises
        ------
        BadConfigurationException
            If no BugZoo snapshot can be found with the given name.
        BadConfigurationException
            If the given BugZoo snapshot is not installed.
        """
        bz = environment.bugzoo
        if not cfg.snapshot in bz.bugs:
            m = f"snapshot not found: {cfg.snapshot}"
            raise BadConfigurationException(m)

        snapshot = bz.bugs[cfg.snapshot]
        image = snapshot.image
        tests = TestSuite.from_config(cfg.tests, environment, snapshot)
        source_directory = snapshot.source_dir
        build_instructions, build_instructions_for_coverage = \
            BuildInstructions.from_bugzoo(snapshot)

        return ProgramDescription(
                    environment=environment,
                    image=image,
                    build_instructions=build_instructions,
                    build_instructions_for_coverage=build_instructions_for_coverage,
                    snapshot=snapshot,
                    source_directory=source_directory,
                    tests=tests)

    def execute(self,
                container: ProgramContainer,
                test: Test,
                *,
                coverage: bool = False
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

        Returns
        -------
        TestOutcome
            A concise summary of the test execution.
        """
        return self.tests.execute(container, test)

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
        with ProgramContainer.for_bugzoo_snapshot(self._environment,
                                                  self.snapshot
                                                  ) as container:
            try:
                container.patch(patch)
            except FailedToApplyPatch:
                logger.debug("failed to apply patch: %s", patch)
                raise BuildFailure

            mgr_ctr = self._environment.bugzoo.containers
            outcome = mgr_ctr.build(container._bugzoo)
            if not outcome.successful:
                raise BuildFailure

            yield container
