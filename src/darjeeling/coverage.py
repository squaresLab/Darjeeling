# -*- coding: utf-8 -*-
__all__ = ('coverage_for_snapshot', 'coverage_for_container',
           'coverage_for_test', 'coverage_for_program', 'coverage_for_config')

from typing import Set
import logging
import functools

from bugzoo import Bug as Snapshot, Container as BugZooContainer

from .config import CoverageConfig
from .container import ProgramContainer
from .core import (FileLineSet, FileLine, TestCoverageMap, Test, TestCoverage,
                   TestOutcome)
from .environment import Environment
from .test import TestSuite
from .program import Program

logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def coverage_for_config(environment: Environment,
                        program: Program,
                        cfg: CoverageConfig
                        ) -> TestCoverageMap:
    if cfg.load_from_file:
        fn_coverage = cfg.load_from_file
        logger.info("loading coverage from file: %s", fn_coverage)
        coverage = TestCoverageMap.from_file(fn_coverage)
    else:
        coverage = coverage_for_program(environment, program)

    if cfg.restrict_to_files:
        coverage = coverage.restrict_to_files(cfg.restrict_to_files)

    if cfg.restrict_to_lines:
        coverage = coverage.restrict_to_locations(cfg.restrict_to_lines)

    return coverage


def coverage_for_program(environment: Environment,
                         program: Program
                         ) -> TestCoverageMap:
    return coverage_for_snapshot(environment, program.snapshot, program.tests)


def coverage_for_snapshot(environment: Environment,
                          snapshot: Snapshot,
                          tests: TestSuite
                          ) -> TestCoverageMap:
    with ProgramContainer.for_bugzoo_snapshot(environment,
                                              snapshot
                                              ) as container:
        logger.debug("computing coverage for snapshot: %s", snapshot.name)
        return coverage_for_container(environment, container, tests)


def coverage_for_container(environment: Environment,
                           container: ProgramContainer,
                           tests: TestSuite
                           ) -> TestCoverageMap:
    bz = environment.bugzoo
    logger.debug("instrumenting container for coverage...")
    bz.containers.instrument(container._bugzoo)
    logger.debug("instrumented container for coverage")
    coverage = functools.partial(coverage_for_test, environment, container, tests)
    return TestCoverageMap({test.name: coverage(test) for test in tests})


def coverage_for_test(environment: Environment,
                      container: ProgramContainer,
                      tests: TestSuite,
                      test: Test
                      ) -> TestCoverage:
    bz = environment.bugzoo
    logger.debug("computing coverage for test [%s]", test.name)
    outcome: TestOutcome = tests.execute(container, test)
    logger.debug("test outcome [%s]: %s", test.name, outcome)
    logger.debug("extracting coverage for test [%s]", test.name)
    lines: Set[FileLine] = bz.containers.extract_coverage(container._bugzoo)
    lines = FileLineSet.from_iter(lines)
    logger.debug("extracted coverage for test [%s]:\n%s", test.name, lines)
    return TestCoverage(test=test.name, outcome=outcome, lines=lines)
