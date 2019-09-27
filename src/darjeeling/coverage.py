# -*- coding: utf-8 -*-
__all__ = ('coverage_for_snapshot', 'coverage_for_container',
           'coverage_for_test', 'coverage_for_program', 'coverage_for_config')

from typing import Set
import logging
import functools

from bugzoo import (Client as BugZooClient,
                    Bug as Snapshot,
                    Container as BugZooContainer)

from .config import CoverageConfig
from .core import FileLine, TestCoverageMap, Test, TestCoverage, TestOutcome
from .test import TestSuite
from .program import Program

logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def coverage_for_config(bz: BugZooClient,
                        program: Program,
                        cfg: CoverageConfig
                        ) -> TestCoverageMap:
    coverage = coverage_for_program(bz, program)
    if cfg.restrict_to_files:
        coverage = coverage.restrict_to_files(cfg.restrict_to_files)
    return coverage


def coverage_for_program(bz: BugZooClient,
                         program: Program
                         ) -> TestCoverageMap:
    return coverage_for_snapshot(bz, program.snapshot, program.tests)


def coverage_for_snapshot(bz: BugZooClient,
                          snapshot: Snapshot,
                          tests: TestSuite
                          ) -> TestCoverageMap:
    logger.debug("computing coverage for snapshot: %s", snapshot.name)
    container: BugZooContainer = bz.containers.provision(snapshot)
    try:
        return coverage_for_container(bz, container, tests)
    finally:
        del bz.containers[container.uid]


def coverage_for_container(bz: BugZooClient,
                           container: BugZooContainer,
                           tests: TestSuite
                           ) -> TestCoverageMap:
    logger.debug("instrumenting container for coverage...")
    bz.containers.instrument(container)
    logger.debug("instrumented container for coverage")
    coverage = functools.partial(coverage_for_test, bz, container, tests)
    return TestCoverageMap({test.name: coverage(test) for test in tests})


def coverage_for_test(bz: BugZooClient,
                      container: BugZooContainer,
                      tests: TestSuite,
                      test: Test
                      ) -> TestCoverage:
    logger.debug("computing coverage for test [%s]", test.name)
    outcome: TestOutcome = tests.execute(container, test)
    logger.debug("test outcome [%s]: %s", test.name, outcome)
    logger.debug("extracting coverage for test [%s]", test.name)
    lines: Set[FileLine] = bz.containers.extract_coverage(container)
    logger.debug("extracted coverage for test [%s]:\n%s", test.name, lines)
    return TestCoverage(test=test.name, outcome=outcome, lines=lines)
