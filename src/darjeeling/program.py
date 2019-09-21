# -*- coding: utf-8 -*-
__all__ = ('Program',)

from typing import Iterator
import contextlib

from bugzoo import Client as BugZooClient, Bug as Snapshot
from bugzoo.core.container import Container
from bugzoo.core.patch import Patch
import attr

from .core import Test, TestOutcome
from .test import TestSuite, BugZooTestSuite
from .config import Config
from .exceptions import BadConfigurationException, BuildFailure


@attr.s(frozen=True, slots=True, auto_attribs=True)
class Program:
    _bugzoo: BugZooClient
    snapshot: Snapshot
    tests: TestSuite

    @staticmethod
    def from_config(bz: BugZooClient, cfg: Config) -> 'Program':
        """Loads a program from a given configuration.

        Raises
        ------
        BadConfigurationException
            If no BugZoo snapshot can be found with the given name.
        BadConfigurationException
            If the given BugZoo snapshot is not installed.
        """
        if not cfg.snapshot in bz.bugs:
            m = f"snapshot not found: {cfg.snapshot}"
            raise BadConfigurationException(m)

        snapshot = bz.bugs[cfg.snapshot]
        tests = TestSuite.from_config(cfg.tests, bz, snapshot)

        if not bz.bugs.is_installed(snapshot):
            m = f"snapshot not installed: {cfg.snapshot}"
            raise BadConfigurationException(m)

        return Program(bz, snapshot, tests)

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
        mgr_ctr = self._bugzoo.containers
        container = None
        try:
            container = mgr_ctr.provision(self.snapshot)
            mgr_ctr.patch(container, patch)
            outcome = mgr_ctr.build(container)
            if not outcome.successful:
                raise BuildFailure
            yield container
        finally:
            if container is not None:
                del mgr_ctr[container.uid]
