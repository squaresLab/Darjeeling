# -*- coding: utf-8 -*-
__all__ = ('Program',)

from typing import Iterator
import contextlib
import logging

from bugzoo import Bug as Snapshot
from bugzoo.core.container import Container
from bugzoo.core.patch import Patch
import attr

from .core import Test, TestOutcome
from .environment import Environment
from .test import TestSuite, BugZooTestSuite
from .config import Config
from .exceptions import BadConfigurationException, BuildFailure

logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@attr.s(frozen=True, slots=True, auto_attribs=True)
class Program:
    """Provides a description of a program.

    Attributes
    ----------
    image: str
        The name of the Docker image for this progrma.
    snapshot:
        The BugZoo snapshot for this program.
    tests: TestSuite
        The test suite for this program.
    """
    _environment: Environment
    image: str
    snapshot: Snapshot
    tests: TestSuite

    @staticmethod
    def from_config(environment: Environment, cfg: Config) -> 'Program':
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

        return Program(environment=environment,
                       image=image,
                       snapshot=snapshot,
                       tests=tests)

    def execute(self, container: Container, test: Test) -> TestOutcome:
        """Executes a given test in a container."""
        return self.tests.execute(container, test)

    @contextlib.contextmanager
    def build(self, patch: Patch) -> Iterator[Container]:
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
        mgr_ctr = self._environment.bugzoo.containers
        container = None
        try:
            container = mgr_ctr.provision(self.snapshot)
            if not mgr_ctr.patch(container, patch):
                logger.debug("failed to apply patch: %s", patch)
                raise BuildFailure
            outcome = mgr_ctr.build(container)
            if not outcome.successful:
                raise BuildFailure
            yield container
        finally:
            if container is not None:
                del mgr_ctr[container.uid]
