# -*- coding: utf-8 -*-
__all__ = ('coverage_for_snapshot', 'coverage_for_container')

from bugzoo import (Client as BugZooClient,
                    Bug as Snapshot,
                    Container as BugZooContainer)

from .core import TestCoverageMap, TestSuite, Test


def coverage_for_snapshot(bz: BugZooClient,
                          snapshot: Snapshot,
                          tests: TestSuite
                          ) -> TestCoverageMap:
    container: BugZooContainer = bz.containers.provision(snapshot)
    try:
        return coverage_for_container(bz, container, tests)
    finally:
        del bz.containers[container.uid]


def coverage_for_container(bz: BugZooClient,
                           container: BugZooContainer,
                           tests: TestSuite
                           ) -> TestCoverageMap:
    raise NotImplementedError
