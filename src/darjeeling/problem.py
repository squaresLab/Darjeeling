from __future__ import annotations

__all__ = ("Problem",)

import functools
import typing
from collections.abc import Iterable, Iterator, Sequence
from typing import Optional

import attr
from bugzoo.core.bug import Bug
from kaskara.analysis import Analysis
from loguru import logger

from darjeeling.core import FileLine, FileLineSet, Test
from darjeeling.exceptions import NoFailingTests, NoImplicatedLines
from darjeeling.source import ProgramSource, ProgramSourceLoader

if typing.TYPE_CHECKING:
    from darjeeling.config import Config, OptimizationsConfig
    from darjeeling.core import Language, TestCoverageMap
    from darjeeling.environment import Environment
    from darjeeling.localization import Localization
    from darjeeling.program import ProgramDescription
    from darjeeling.test import TestSuite


@attr.s(auto_attribs=True, frozen=True)
class Problem:
    """Used to provide a description of a problem (i.e., a bug), and to hold
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
    localization: Localization
        Fault localization based on the associated test suite.
    """
    environment: Environment
    config: Config
    language: Language
    coverage: TestCoverageMap
    sources: ProgramSource
    program: ProgramDescription
    failing_tests: Sequence[Test]
    passing_tests: Sequence[Test]
    test_ordering: Iterable[Test]
    analysis: Optional[Analysis]
    localization: Localization

    @staticmethod
    def build(environment: Environment,
              config: Config,
              language: Language,
              coverage: TestCoverageMap,
              program: ProgramDescription,
              localization: Localization,
              *,
              analysis: Optional[Analysis] = None,
              ) -> Problem:
        """Constructs a problem description.

        Raises
        ------
        NoFailingTests
            If the program under repair has no failing tests.
        NoImplicatedLines
            If no lines are implicated by the coverage information and the
            provided suspiciousness metric.
        """
        logger.debug("using coverage to determine passing and failing tests")
        failing_tests: Sequence[Test] = \
            tuple(program.tests[name] for name in sorted(coverage)
                  if not coverage[name].outcome.successful)
        passing_tests: Sequence[Test] = \
            tuple(program.tests[name] for name in sorted(coverage)
                  if coverage[name].outcome.successful)

        logger.info("determined passing and failing tests")
        logger.info("* passing tests: {}",
                    ", ".join([t.name for t in passing_tests]))
        logger.info("* failing tests: {}",
                    ", ".join([t.name for t in failing_tests]))
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
        logger.info("test order: {}", ", ".join(t.name for t in test_ordering))

        logger.debug("storing contents of source code files")
        source_files = set(location.filename for location in coverage.failing.locations)
        source_loader = ProgramSourceLoader(environment)
        sources = source_loader.for_program(program, files=source_files)
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
                          localization=localization,
                          test_ordering=test_ordering)
        problem.validate()
        return problem

    def validate(self) -> None:
        """Ensures that this repair problem is valid. To be considered valid, a
        repair problem must have at least one failing test case and one
        implicated line.
        """
        files = set(self.implicated_files)
        lines = FileLineSet.from_iter(self.lines)
        logger.info("implicated lines [{}]:\n{}", len(lines), lines)
        logger.info("implicated files [{}]:\n* {}", len(files),
                    "\n* ".join(files))
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
    def test_suite(self) -> TestSuite:  # type: ignore[type-arg]
        return self.program.tests

    @property
    def lines(self) -> Iterator[FileLine]:
        """Returns an iterator over the lines that are implicated by the
        description of this problem.
        """
        yield from self.coverage.failing.locations

    @property
    def implicated_files(self) -> Iterator[str]:
        yield from set(location.filename for location in self.coverage.failing.locations)
