from typing import List, Optional, Dict, Iterator, Callable, Set
from timeit import default_timer as timer
import tempfile
import logging
import os

import boggart
import rooibos
import bugzoo
import bugzoo.localization.suspiciousness as metrics
from rooibos import Client as RooibosClient
from bugzoo.core.fileline import FileLine, FileLineSet
from bugzoo.core.bug import Bug
from bugzoo.core.patch import Patch
from bugzoo.core.coverage import TestSuiteCoverage
from bugzoo.core.spectra import Spectra
from bugzoo.localization import SuspiciousnessMetric, Localization
from bugzoo.testing import TestCase
from bugzoo.util import indent

import darjeeling.filters as filters
from .snippet import SnippetDatabase, Snippet
from .source import ProgramSourceManager
from .util import get_file_contents
from .exceptions import NoFailingTests, NoImplicatedLines


logger = logging.getLogger(__name__)  # type: logging.Logger


class Problem(object):
    """
    Used to provide a description of a problem (i.e., a bug), and to hold
    information pertinent to its solution (e.g., coverage, transformations).
    """
    def __init__(self,
                 bz: bugzoo.BugZoo,
                 bug: Bug,
                 coverage: TestSuiteCoverage,
                 *,
                 client_rooibos: Optional[RooibosClient] = None,
                 suspiciousness_metric: Optional[SuspiciousnessMetric] = None,
                 restrict_to_lines: Optional[FileLineSet] = None,
                 line_coverage_filters: Optional[List[Callable[[str], bool]]] = None
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
        assert len(in_files) > 0
        self.__bug = bug
        self.__client_rooibos = client_rooibos
        self.__client_bugzoo = bz
        self.__coverage = coverage
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
        logger.info("* passing tests: %s", ', '.join([t.name for t in self.__tests_passing]))
        logger.info("* failing tests: %s", ', '.join([t.name for t in self.__tests_failing]))
        if not self.__tests_failing:
            raise NoFailingTests

        # determine the implicated lines
        # 0. we already restricted to lines that occur in specified files
        # 1. restrict to lines covered by failing tests
        # 3. restrict to lines with suspiciousness greater than zero
        # 4. restrict to lines that are optionally provided
        logger.info("Determining implicated lines")
        self.__lines = self.__coverage.failing.lines

        if restrict_to_lines is not None:
            self.__lines = self.__lines.intersection(restrict_to_lines)

        # TODO migrate
        # cache contents of the implicated files
        t_start = timer()
        logger.debug("storing contents of source code files")
        self.__sources = ProgramSourceManager(bz,
                                              client_rooibos,
                                              bug,
                                              files=self.__lines.files)
        duration = timer() - t_start
        logger.debug("stored contents of source code files (took %.1f seconds)",
                            duration)

        # restrict attention to statements
        # FIXME for now, we approximate this -- going forward, we can use
        #   Rooibos to determine transformation targets
        num_lines_before_filtering = len(self.__lines)
        logger.debug("filtering lines according to content filters")
        line_content_filters = [
            filters.ends_with_semi_colon,
            filters.has_balanced_delimiters
        ]
        if line_coverage_filters:
            line_content_filters += line_coverage_filters # type: ignore
        for f in line_content_filters:
            )
            self.__lines = self.__lines.filter(fltr_line)
        num_lines_after_filtering = len(self.__lines)
        num_lines_removed_by_filtering = \
            num_lines_after_filtering - num_lines_before_filtering
        logger.debug("filtered lines according to content files: removed %d lines",  # noqa: pycodestyle
                            num_lines_removed_by_filtering)

        # construct the snippet database from the parts of the program that
        # were executed by the test suite (both passing and failing tests)
        # TODO add a snippet extractor component
        logger.info("constructing snippet database")
        self.__snippets = SnippetDatabase()

        # TODO allow additional snippet filters to be provided as params
        snippet_filters = [
            filters.ends_with_semi_colon,
            filters.has_balanced_delimiters
        ]

        for line in self.__coverage.lines:
            content = self.__sources.read_line(line).strip()
            if all(fltr(content) for fltr in snippet_filters):
                # logger.debug("* found snippet at %s: %s", line, content)
                snippet = Snippet(content)
                self.__snippets.add(snippet, origin=line)

        logger.info("construct snippet database: %d snippets",
                           len(self.__snippets))
        for fn in self.__lines.files:
            logger.info("* %d unique snippets in %s",
                               len(list(self.__snippets.in_file(fn))), fn)

        logger.debug("reducing memory footprint by discarding extraneous data")
        self.__coverage.restricted_to_files(self.__lines.files)
        self.__spectra.restricted_to_files(self.__lines.files)
        extraneous_source_fns = \
            set(self.__sources.files) - set(self.__lines.files)
        for fn in extraneous_source_fns:
            del self.__sources[fn]
        logger.debug("finished reducing memory footprint")

    def _dump_coverage(self) -> None:
        logger.debug("[COVERAGE]\n%s\n[/COVERAGE]",
                            indent(str(self.__coverage), 2))


    def restrict_to_files(self, filenames: List[str]) -> None:
        """
        Restricts the scope of the repair to the intersection of the files
        that are currently within the scope of the repair and a set of
        provided files.
        """
        logger.info("restricting repair to files: %s", filenames)
        self.__coverage = self.__coverage.restricted_to_files(filenames)
        # FIXME what else do we need to recompute?
        logger.info("successfully restricted repair to given files.")
        self._dump_coverage()


        # TODO remove any extraneous files from the source manager
        self.validate()

    def restrict_with_filter(self,
                             fltr: Callable[[str], bool]
                             ) -> None:
        """
        Uses a given filter to remove certain lines from the scope of the
        repair.
        """
        f = lambda fl: fltr(self.__sources.read_line(fl)
        filtered = [l for l in self.lines if f(l)]  # type: List[FileLine]
        self.restrict_to_lines(filtered)

    def validate(self) -> None:
        """
        Ensures that this repair problem is valid. To be considered valid, a
        repair problem must have at least one failing test case and one
        implicated line.
        """
        logger.info("implicated lines [%d]:\n%s",
                           len(self.__lines), self.__lines)
        logger.info("implicated files [%d]:\n* %s",
                           len(self.__lines.files),
                           '\n* '.join(self.__lines.files))
        if len(self.__lines) == 0:
            raise NoImplicatedLines

        raise NotImplementedError

    def restrict_to_lines(self, lines: Iterator[FileLine]) -> None:
        raise NotImplementedError

    @property
    def snippets(self) -> SnippetDatabase:
        """
        The snippet database that should be used to generate new code.
        """
        return self.__snippets

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
        for test in self.__tests_failing:
            yield test
        for test in self.__tests_passing:
            yield test

    @property
    def tests_failing(self) -> Iterator[TestCase]:
        """
        Returns an iterator over the failing tests for this problem.
        """
        return self.__tests_failing.__iter__()

    @property
    def tests_passing(self) -> Iterator[TestCase]:
        """
        Returns an iterator over the passing tests for this problem.
        """
        return self.__tests_passing.__iter__()

    @property
    def coverage(self) -> TestSuiteCoverage:
        """
        Line coverage information for each test within the test suite for the
        program under repair.
        """
        return self.__coverage

    @property
    def spectra(self) -> Spectra:
        """
        Provides a concise summary of the number of passing and failing tests
        that cover each implicated line.
        """
        return self.__spectra

    @property
    def lines(self) -> Iterator[FileLine]:
        """
        Returns an iterator over the lines that are implicated by the
        description of this problem.
        """
        return self.__lines.__iter__()

    @property
    def sources(self) -> ProgramSourceManager:
        """
        The source code files for the program under repair.
        """
        return self.__sources
