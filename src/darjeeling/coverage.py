# -*- coding: utf-8 -*-
__all__ = ('coverage_for_snapshot', 'coverage_for_container',
           'coverage_for_test')

from typing import Set
import functools

from bugzoo import (Client as BugZooClient,
                    Bug as Snapshot,
                    Container as BugZooContainer)

from .core import (FileLine, TestCoverageMap, TestSuite, Test, TestCoverage,
                   TestOutcome)


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
    bz.containers.instrument(container)
    coverage = functools.partial(coverage_for_test, bz, container, tests)
    return TestCoverageMap({test.name: coverage(test) for test in tests})


def coverage_for_test(bz: BugZooClient,
                      container: BugZooContainer,
                      tests: TestSuite,
                      test: Test
                      ) -> TestCoverage:
    outcome: TestOutcome = tests.execute(container, test)
    lines: Set[FileLine] = bz.containers.extract_coverage(container)
    return TestCoverage(test=test.name, outcome=outcome, lines=lines)
