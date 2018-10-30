from typing import List, Optional, Dict, Iterator, Callable, Set, Iterable
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
from bugzoo.core.coverage import TestSuiteCoverage
from bugzoo.core.test import TestCase
from bugzoo.compiler import CompilationOutcome as BuildOutcome
from bugzoo.util import indent
from kaskara.analysis import Analysis

from .core import Language
from .source import ProgramSourceManager
from .util import get_file_contents
from .exceptions import NoFailingTests, NoImplicatedLines, BuildFailure
from .settings import Settings


logger = logging.getLogger(__name__)  # type: logging.Logger


class Problem(object):
    """
    Used to provide a description of a problem (i.e., a bug), and to hold
    information pertinent to its solution (e.g., coverage, transformations).
    """
    def __init__(self,
                 bz: bugzoo.BugZoo,
                 bug: Bug,
                 language: Language,
                 coverage: TestSuiteCoverage,
                 *,
                 analysis: Optional[Analysis] = None,
                 client_rooibos: Optional[RooibosClient] = None,
                 settings: Optional[Settings] = None,
                 restrict_to_files: Optional[List[str]] = None
                 ) -> None:
        """
        Constructs a Darjeeling problem description.

        Params:
            bug: A description of the faulty program.
            coverage: Used to provide coverage information for the program
                under test.

        Raises:
            NoFailingTests: if the program under repair has no failing tests.
            NoImplicatedLines: if no lines are implicated by the coverage
                information and the provided suspiciousness metric.
        """
        self.__bug = bug
        self.__language = language
        self.__client_rooibos = client_rooibos
        self.__client_bugzoo = bz
        self.__coverage = coverage
        self.__analysis = analysis
        self.__settings = settings if settings else Settings()
        self._dump_coverage()

        # determine the passing and failing tests
        logger.debug("using test execution used to generate coverage to determine passing and failing tests")
        self.__tests_failing = set()  # type: Set[TestCase]
        self.__tests_passing = set()  # type: Set[TestCase]
        for test_name in self.__coverage:
            test = bug.harness[test_name]
            test_coverage = self.__coverage[test_name]
            if test_coverage.outcome.passed:
                self.__tests_passing.add(test)
            else:
                self.__tests_failing.add(test)

        logger.info("determined passing and failing tests")
        logger.info("* passing tests: %s",
                    ', '.join([t.name for t in self.__tests_passing]))
        logger.info("* failing tests: %s",
                    ', '.join([t.name for t in self.__tests_failing]))
        if not self.__tests_failing:
            raise NoFailingTests

        # perform test ordering
        def ordering(x: TestCase, y: TestCase) -> int:
            cov_x = self.__coverage[x.name]
            cov_y = self.__coverage[y.name]
            pass_x = cov_x.outcome.passed
            pass_y = cov_y.outcome.passed
            time_x = cov_x.outcome.duration
            time_y = cov_y.outcome.duration

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
            sorted(bug.tests,
                   key=functools.cmp_to_key(ordering)) # type: List[TestCase]
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
                                              bug,
                                              files=source_files)
        logger.debug("stored contents of source code files (took %.1f seconds)",
                     timer() - t_start)

    def _dump_coverage(self) -> None:
        logger.debug("[COVERAGE]\n%s\n[/COVERAGE]",
                     indent(str(self.__coverage), 2))

    def __remove_redundant_sources(self) -> None:
        logger.debug("reducing memory footprint by discarding extraneous data")
        source_files = set(self.__sources.files)  # type: Set[str]
        covered_files = set(self.__coverage.lines.files)  # type: Set[str]
        extraneous_files = covered_files - source_files
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
            container = mgr_ctr.provision(self.__bug)
            mgr_ctr.patch(container, patch)
            if builder is None:
                outcome = mgr_ctr.build(container)
            else:
                outcome = builder(container)
            # logger.debug("build outcome for %s:\n%s",
            #              candidate,
            #              outcome.response.output)
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
        self.__coverage = self.__coverage.restricted_to_files(filenames)
        logger.info("successfully restricted repair to given files.")
        self._dump_coverage()
        self.__remove_redundant_sources()
        self.validate()

    def restrict_to_lines(self, lines: Iterable[FileLine]) -> None:
        """
        Restricts the scope of the repair to the intersection of the current
        set of implicated lines and a provided set of lines.
        """
        self.__coverage = self.__coverage.restricted_to_lines(lines)
        self._dump_coverage()
        self.__remove_redundant_sources()
        self.validate()

    def restrict_with_filter(self,
                             fltr: Callable[[str], bool]
                             ) -> None:
        """
        Uses a given filter to remove certain lines from the scope of the
        repair.
        """
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
    def language(self) -> Language:
        return self.__language

    @property
    def bugzoo(self) -> BugZooClient:
        return self.__client_bugzoo

    @property
    def settings(self) -> Settings:
        return self.__settings

    @property
    def analysis(self) -> Optional[Analysis]:
        """
        Results of an optional static analysis for the progrram under repair.
        """
        return self.__analysis

    @property
    def rooibos(self) -> RooibosClient:
        assert self.__client_rooibos is not None
        assert isinstance(self.__client_rooibos, rooibos.Client)
        return self.__client_rooibos

    @property
    def bug(self) -> Bug:
        """
        A description of the bug, provided by BugZoo.
        """
        return self.__bug

    @property
    def tests(self) -> Iterator[TestCase]:
        """
        Returns an iterator over the tests for this problem.
        """
        yield from self.__tests_ordered

    @property
    def failing_tests(self) -> Iterator[TestCase]:
        yield from self.__tests_failing

    @property
    def passing_tests(self) -> Iterator[TestCase]:
        yield from self.__tests_passing

    @property
    def coverage(self) -> TestSuiteCoverage:
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
        return self.__coverage.failing.lines.__iter__()

    @property
    def implicated_files(self) -> Iterator[str]:
        return self.__coverage.failing.lines.files

    @property
    def sources(self) -> ProgramSourceManager:
        """
        The source code files for the program under repair.
        """
        return self.__sources
