# -*- coding: utf-8 -*-
__all__ = ('Problem',)

from typing import (List, Optional, Dict, Iterator, Callable, Set, Iterable,
                    Mapping, Sequence)
from timeit import default_timer as timer
import tempfile
import logging
import functools
import os

import attr
from bugzoo.core.fileline import FileLine, FileLineSet
from bugzoo.core.bug import Bug
from kaskara.analysis import Analysis

from .core import Language, Test, TestCoverage, TestCoverageMap
from .config import Config
from .environment import Environment
from .program import Program
from .source import ProgramSource, ProgramSourceLoader
from .exceptions import NoFailingTests, NoImplicatedLines, BuildFailure
from .config import OptimizationsConfig
from .test import TestSuite

logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@attr.s(auto_attribs=True, frozen=True)
class Problem:
    """
    Used to provide a description of a problem (i.e., a bug), and to hold
    information pertinent to its solution (e.g., coverage).

    Attributes
    ----------
    config: Config
        The repair configuration being used.
    coverage: TestCoverageMap
        Line coverage for each test within the test suite for the program
        under repair.
    sources: ProgramSource
        The source code files for the program under repair.
    analysis: Analysis, optional
        Results of an optional static analysis for the program.
    failing_tests: Sequence[Test]
        The failing tests for this problem.
    passing_tests: Sequence[Test]
        The passing tests for this problem.
    test_ordering: Iterable[Test]
        The order in which tests should be executed.
    """
    environment: Environment
    config: Config
    language: Language
    coverage: TestCoverageMap
    sources: ProgramSource
    program: Program
    failing_tests: Sequence[Test]
    passing_tests: Sequence[Test]
    test_ordering: Iterable[Test]
    analysis: Optional[Analysis]

    @staticmethod
    def build(environment: Environment,
              config: Config,
              language: Language,
              coverage: TestCoverageMap,
              program: Program,
              *,
              analysis: Optional[Analysis] = None
              ) -> 'Problem':
        """Constructs a problem description.

        Raises
        -------
        NoFailingTests
            If the program under repair has no failing tests.
        NoImplicatedLines
            If no lines are implicated by the coverage information and the
            provided suspiciousness metric.
        """
        bz = environment.bugzoo
        logger.debug('using coverage to determine passing and failing tests')
        failing_tests: Sequence[Test] = \
            tuple(program.tests[name] for name in sorted(coverage)
                  if not coverage[name].outcome.successful)
        passing_tests: Sequence[Test] = \
            tuple(program.tests[name] for name in sorted(coverage)
                  if coverage[name].outcome.successful)

        logger.info('determined passing and failing tests')
        logger.info('* passing tests: %s',
                    ', '.join([t.name for t in passing_tests]))
        logger.info('* failing tests: %s',
                    ', '.join([t.name for t in failing_tests]))
        if not failing_tests:
            raise NoFailingTests

        # perform test ordering
        def ordering(x: Test, y: Test) -> int:
            cov_x = coverage[x.name]
            cov_y = coverage[y.name]
            pass_x = cov_x.outcome.successful
            pass_y = cov_y.outcome.successful
            time_x = cov_x.outcome.time_taken
            time_y = cov_y.outcome.time_taken

            # prioritise failing tests over non-failing tests
            if pass_x and not pass_y:
                return 1
            elif not pass_x and pass_y:
                return -1

            # if x and y have the same outcome, prioritise the fastest
            elif time_x < time_y:
                return -1
            elif time_x > time_y:
                return 1
            else:
                return 0

        logger.info("ordering test cases")
        test_ordering: Sequence[Test] = \
            tuple(sorted(program.tests, key=functools.cmp_to_key(ordering)))
        logger.info('test order: %s', ', '.join(t.name for t in test_ordering))

        logger.debug("storing contents of source code files")
        source_files = set(l.filename for l in coverage.failing.locations)
        source_loader = ProgramSourceLoader(bz)
        sources = source_loader.for_bugzoo_snapshot(program.snapshot,
                                                    files=source_files)
        logger.debug("stored contents of source code files")

        problem = Problem(environment=environment,
                          program=program,
                          analysis=analysis,
                          language=language,
                          coverage=coverage,
                          sources=sources,
                          config=config,
                          passing_tests=passing_tests,
                          failing_tests=failing_tests,
                          test_ordering=test_ordering)
        problem.validate()
        return problem

    def validate(self) -> None:
        """
        Ensures that this repair problem is valid. To be considered valid, a
        repair problem must have at least one failing test case and one
        implicated line.
        """
        lines = list(self.lines)
        files = set(self.implicated_files)
        logger.info("implicated lines [%d]:\n%s", len(lines), lines)
        logger.info("implicated files [%d]:\n* %s", len(files),
                    '\n* '.join(files))
        if len(lines) == 0:
            raise NoImplicatedLines

    @property
    def settings(self) -> OptimizationsConfig:
        return self.config.optimizations

    @property
    def bug(self) -> Bug:
        """A description of the bug, provided by BugZoo."""
        return self.program.snapshot

    @property
    def tests(self) -> Iterator[Test]:
        """Returns an iterator over the tests for this problem."""
        yield from self.test_ordering

    @property
    def test_suite(self) -> TestSuite:
        return self.program.tests

    @property
    def lines(self) -> Iterator[FileLine]:
        """
        Returns an iterator over the lines that are implicated by the
        description of this problem.
        """
        yield from self.coverage.failing.locations

    @property
    def implicated_files(self) -> Iterator[str]:
        yield from set(l.filename for l in self.coverage.failing.locations)
