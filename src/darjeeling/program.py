# -*- coding: utf-8 -*-
__all__ = ('Program',)

from typing import Iterator
import contextlib

from bugzoo import Client as BugZooClient, Bug as Snapshot
from bugzoo.core.container import Container
from bugzoo.core.patch import Patch
import attr

from .core import Test, TestOutcome, TestSuite
from .test import BugZooTestSuite
from .config import Config
from .exceptions import BadConfigurationException


@attr.s(frozen=True, slots=True, auto_attribs=True)
class Program:
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

        if not client_bugzoo.bugs.is_installed(snapshot):
            m = f"snapshot not installed: {cfg.snapshot}"
            raise BadConfigurationException(m)

        tests = BugZooTestSuite.from_bug(bz, snapshot)

        return Program(snapshot, tests)

    def execute(self, container: Container, test: Test) -> TestOutcome:
        """Executes a given test in a container."""
        raise NotImplementedError

    @contextlib.contextmanager
    def build(self, patch: Patch) -> Iterator[Container]:
        """Builds a container for a given patch."""
        raise NotImplementedError
