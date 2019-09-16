# -*- coding: utf-8 -*-
__all__ = ('Problem',)

from typing import (List, Optional, Dict, Iterator, Callable, Set, Iterable,
                    Mapping, Sequence)
from timeit import default_timer as timer
import tempfile
import logging
import functools
import os

import boggart
import rooibos
import bugzoo
from rooibos import Client as RooibosClient
from bugzoo.client import Client as BugZooClient
from bugzoo.core.fileline import FileLine, FileLineSet
from bugzoo.core.container import Container
from bugzoo.core.bug import Bug
from bugzoo.core.patch import Patch
from bugzoo.compiler import CompilationOutcome as BuildOutcome
from bugzoo.util import indent
from kaskara.analysis import Analysis

from .core import Language, Test, TestSuite, TestCoverage, TestCoverageMap
from .program import Program
from .source import ProgramSourceManager
from .util import get_file_contents
from .exceptions import NoFailingTests, NoImplicatedLines, BuildFailure
from .config import OptimizationsConfig
from .test import TestSuite

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)


class Problem:
    """
    Used to provide a description of a problem (i.e., a bug), and to hold
    information pertinent to its solution (e.g., coverage, transformations).
    """
    def __init__(self,
                 bz: bugzoo.BugZoo,
                 language: Language,
                 coverage: TestCoverageMap,
                 program: Program,
                 *,
                 analysis: Optional[Analysis] = None,
                 client_rooibos: Optional[RooibosClient] = None,
                 settings: Optional[OptimizationsConfig] = None,
                 restrict_to_files: Optional[List[str]] = None
                 ) -> None:
        """Constructs a Darjeeling problem description.

        Params:
            bug: A description of the faulty program.
            coverage: Used to provide coverage information for the program
                under test.

        Raises:
            NoFailingTests: if the program under repair has no failing tests.
            NoImplicatedLines: if no lines are implicated by the coverage
                information and the provided suspiciousness metric.
        """
        self.__language = language
        self.__client_rooibos = client_rooibos
        self.__client_bugzoo = bz
        self.__coverage: TestCoverageMap = coverage
        self.__analysis = analysis
        self.__settings = settings if settings else OptimizationsConfig()
        self.__program = program
        self._dump_coverage()

        # use coverage to determine the passing and failing tests
        logger.debug("using test execution used to generate coverage to determine passing and failing tests")
        test_suite = program.tests
        self.__tests_failing: Sequence[Test] = \
            tuple(test_suite[name] for name in sorted(self.__coverage)
                  if not self.__coverage[name].outcome.successful)
        self.__tests_passing: Sequence[Test] = \
            tuple(test_suite[name] for name in sorted(self.__coverage)
                  if self.__coverage[name].outcome.successful)

        logger.info("determined passing and failing tests")
        logger.info("* passing tests: %s",
                    ', '.join([t.name for t in self.__tests_passing]))
        logger.info("* failing tests: %s",
                    ', '.join([t.name for t in self.__tests_failing]))
        if not self.__tests_failing:
            raise NoFailingTests

        # perform test ordering
        def ordering(x: Test, y: Test) -> int:
            cov_x = self.__coverage[x.name]
            cov_y = self.__coverage[y.name]
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
        self.__tests_ordered = \
            sorted(program.tests,
                   key=functools.cmp_to_key(ordering)) # type: List[Test]
        logger.info("test order: %s",
                    ', '.join(t.name for t in self.__tests_ordered))

        # FIXME huge bottleneck!
        # cache contents of the implicated files
        t_start = timer()
        logger.debug("storing contents of source code files")
        source_files = set(self.implicated_files)
        if restrict_to_files:
            source_files &= set(restrict_to_files)
        self.__sources = ProgramSourceManager(bz,
                                              client_rooibos,
                                              program.snapshot,
                                              files=source_files)
        logger.debug("stored contents of source code files (took %.1f seconds)",
                     timer() - t_start)

    def _dump_coverage(self) -> None:
        logger.debug("[COVERAGE]\n%s\n[/COVERAGE]",
                     indent(str(self.__coverage), 2))

    def __remove_redundant_sources(self) -> None:
        logger.debug("reducing memory footprint by discarding extraneous data")
        source_files: Set[str] = set(self.__sources.files)
        covered_files: Set[str] = set(l.filename for l in self.__coverage.locations)
        extraneous_files: Set[str] = covered_files - source_files
        for fn in extraneous_files:
            del self.__sources[fn]
        logger.debug("finished reducing memory footprint")

    def build_patch(self,
                    patch: Patch,
                    builder: Optional[Callable[[Container], BuildOutcome]] = None
                    ) -> Container:
        """
        Provisions a container for a given patch and prepares it by building
        the source code.

        Parameters:
            patch: the patch for which a container should be built.
            builder: used to optionally provide a custom function for building
                the code inside the container. If no custom builder is
                provided, then the default one will be used instead.

        Returns:
            a ready-to-use container that contains a built version of the
            patched source code.

        Raises:
            BuildFailure: if the program failed to build.
        """
        mgr_ctr = self.__client_bugzoo.containers
        container = None
        try:
            container = mgr_ctr.provision(self.bug)
            mgr_ctr.patch(container, patch)
            if builder is None:
                outcome = mgr_ctr.build(container)
            else:
                outcome = builder(container)
            # ensure the container is destroyed
            if not outcome.successful:
                raise BuildFailure
        except Exception:
            if container is not None:
                del mgr_ctr[container.uid]
            raise
        return container

    def restrict_to_files(self, filenames: List[str]) -> None:
        """
        Restricts the scope of the repair to the intersection of the files
        that are currently within the scope of the repair and a set of
        provided files.
        """
        logger.info("restricting repair to files: %s", filenames)
        self.__coverage = self.__coverage.restrict_to_files(filenames)
        logger.info("successfully restricted repair to given files.")
        self._dump_coverage()
        self.__remove_redundant_sources()
        self.validate()

    def restrict_to_lines(self, lines: Iterable[FileLine]) -> None:
        """
        Restricts the scope of the repair to the intersection of the current
        set of implicated lines and a provided set of lines.
        """
        self.__coverage = self.__coverage.restrict_to_locations(lines)
        self._dump_coverage()
        self.__remove_redundant_sources()
        self.validate()

    def restrict_with_filter(self,
                             fltr: Callable[[str], bool]
                             ) -> None:
        """Uses a filter to remove certain lines from the scope of repair."""
        f = lambda fl: fltr(self.__sources.read_line(fl))
        filtered = [l for l in self.lines if f(l)]  # type: List[FileLine]
        self.restrict_to_lines(filtered)

    def validate(self) -> None:
        """
        Ensures that this repair problem is valid. To be considered valid, a
        repair problem must have at least one failing test case and one
        implicated line.
        """
        lines = list(self.lines)
        files = list(self.implicated_files)
        logger.info("implicated lines [%d]:\n%s", len(lines), lines)
        logger.info("implicated files [%d]:\n* %s", len(files),
                    '\n* '.join(files))
        if len(lines) == 0:
            raise NoImplicatedLines

    @property
    def program(self) -> Program:
        return self.__program

    @property
    def language(self) -> Language:
        return self.__language

    @property
    def bugzoo(self) -> BugZooClient:
        return self.__client_bugzoo

    @property
    def settings(self) -> OptimizationsConfig:
        return self.__settings

    @property
    def analysis(self) -> Optional[Analysis]:
        """Results of an optional static analysis for the program."""
        return self.__analysis

    @property
    def rooibos(self) -> RooibosClient:
        assert self.__client_rooibos is not None
        assert isinstance(self.__client_rooibos, rooibos.Client)
        return self.__client_rooibos

    @property
    def bug(self) -> Bug:
        """A description of the bug, provided by BugZoo."""
        return self.__program.snapshot

    @property
    def tests(self) -> Iterator[Test]:
        """Returns an iterator over the tests for this problem."""
        yield from self.__tests_ordered

    @property
    def test_suite(self) -> TestSuite:
        return self.__program.tests

    @property
    def failing_tests(self) -> Iterator[Test]:
        yield from self.__tests_failing

    @property
    def passing_tests(self) -> Iterator[Test]:
        yield from self.__tests_passing

    @property
    def coverage(self) -> TestCoverageMap:
        """
        Line coverage information for each test within the test suite for the
        program under repair.
        """
        return self.__coverage

    @property
    def lines(self) -> Iterator[FileLine]:
        """
        Returns an iterator over the lines that are implicated by the
        description of this problem.
        """
        yield from self.__coverage.failing.locations

    @property
    def implicated_files(self) -> Iterator[str]:
        yield from (l.filename for l in self.__coverage.failing.locations)

    @property
    def sources(self) -> ProgramSourceManager:
        """The source code files for the program under repair."""
        return self.__sources
