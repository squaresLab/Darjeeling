from typing import List, Optional, Dict, Iterator, Callable, Set
from timeit import default_timer as timer
import tempfile
import logging
import os

import bugzoo
import bugzoo.localization.suspiciousness as metrics
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
from .source import SourceFile, SourceFileCollection
from .util import get_file_contents
from .exceptions import NoFailingTests, NoImplicatedLines


class Problem(object):
    """
    Used to provide a description of a problem (i.e., a bug), and to hold
    information pertinent to its solution (e.g., coverage, transformations).
    """
    def __init__(self,
                 bz: bugzoo.BugZoo,
                 bug: Bug,
                 *,
                 suspiciousness_metric: Optional[SuspiciousnessMetric] = None,
                 in_files: List[str],
                 restrict_to_lines: Optional[FileLineSet] = None,
                 cache_coverage: bool = True,
                 verbose: bool = False,
                 logger: Optional[logging.Logger] = None,
                 line_coverage_filters: Optional[List[Callable[[str], bool]]] = None
                 ) -> None:
        """
        Constructs a Darjeeling problem description.

        Params:
            bug: A description of the faulty program.
            in_files: An optional list that can be used to restrict the set of
                transformations to those that occur in any files belonging to
                that list. If no list is provided, all source code files will
                be included.
            in_functions: An optional list that can be used to restrict the set
                of transformations to those that occur in any function whose
                name appears in the given list. If no list is provided, no
                filtering of transformations based on the function to which
                they belong will occur.

        Raises:
            NoFailingTests: if the program under repair has no failing tests.
            NoImplicatedLines: if no lines are implicated by the coverage
                information and the provided suspiciousness metric.
        """
        assert len(in_files) > 0
        self.__bug = bug
        self.__verbose = verbose

        # establish logging mechanism
        # * stream logging information to stdout
        if logger:
            self.__logger = logger
        else:
            self.__logger = \
                logging.getLogger('darjeeling.problem').getChild(bug.name)
            self.__logger.setLevel(logging.DEBUG)
            self.__logger.addHandler(logging.StreamHandler())
        self.__logger.debug("creating problem for bug: %s", bug.name)

        if suspiciousness_metric is None:
            self.__logger.debug("no suspiciousness metric provided: using Tarantula as a default.")
            suspiciousness_metric = metrics.tarantula

        # fetch coverage information
        if cache_coverage:
            self.__logger.debug("fetching coverage information from BugZoo")
            self.__coverage = bz.bugs.coverage(bug)
            self.__logger.debug("fetched coverage information from BugZoo")
        else:
            self.__logger.debug("computing coverage information")
            try:
                container = bz.containers.provision(bug)
                self.__coverage = bz.containers.coverage(container)
            finally:
                del bz.containers[container.uid]
            self.__logger.debug("computed coverage information")
        self._dump_coverage()

        # restrict coverage information to specified files
        self.__logger.debug("restricting coverage information to files:\n* %s",
                            '\n* '.join(in_files))
        self.__coverage = self.__coverage.restricted_to_files(in_files)
        self.__logger.debug("restricted coverage information.")
        self._dump_coverage()


        # determine the passing and failing tests by using coverage information
        self.__logger.debug("using test execution used to generate coverage to determine passing and failing tests")
        self.__tests_failing = set() # type: Set[TestCase]
        self.__tests_passing = set() # type: Set[TestCase]
        for test_name in self.__coverage:
            test = bug.harness[test_name]
            test_coverage = self.__coverage[test_name]
            if test_coverage.outcome.passed:
                self.__tests_passing.add(test)
            else:
                self.__tests_failing.add(test)

        self.__logger.info("determined passing and failing tests")
        self.__logger.info("* passing tests: %s", ', '.join([t.name for t in self.__tests_passing]))
        self.__logger.info("* failing tests: %s", ', '.join([t.name for t in self.__tests_failing]))
        if not self.__tests_failing:
            raise NoFailingTests

        # determine the implicated lines
        # 0. we already restricted to lines that occur in specified files
        # 1. restrict to lines covered by failing tests
        # 3. restrict to lines with suspiciousness greater than zero
        # 4. restrict to lines that are optionally provided
        self.__logger.info("Determining implicated lines")
        self.__lines = self.__coverage.failing.lines

        if restrict_to_lines is not None:
            self.__lines = self.__lines.intersection(restrict_to_lines)

        # cache contents of the implicated files
        t_start = timer()
        self.__logger.debug("storing contents of source code files")
        self.__sources = SourceFileCollection.from_bug(bz, bug, self.__lines.files)
        duration = timer() - t_start
        self.__logger.debug("stored contents of source code files (took %.1f seconds)",
                            duration)

        # restrict attention to statements
        # FIXME for now, we approximate this -- going forward, we can use
        #   Rooibos to determine transformation targets
        num_lines_before_filtering = len(self.__lines)
        self.__logger.debug("filtering lines according to content filters")
        line_content_filters = [
            filters.ends_with_semi_colon,
            filters.has_balanced_delimiters
        ]
        if line_coverage_filters:
            line_content_filters += line_coverage_filters # type: ignore
        for f in line_content_filters:
            fltr_line = \
                lambda fl: f(self.__sources.line(fl.filename, fl.num))
            self.__lines = self.__lines.filter(fltr_line)
        num_lines_after_filtering = len(self.__lines)
        num_lines_removed_by_filtering = \
            num_lines_after_filtering - num_lines_before_filtering
        self.__logger.debug("filtered lines according to content files: removed %d lines",  # noqa: pycodestyle
                            num_lines_removed_by_filtering)

        # compute fault localization
        self.__logger.info("computing fault localization")
        self.__coverage = \
            self.__coverage.restricted_to_files(self.__lines.files)
        self.__logger.debug("restricted coverage to implicated files")
        self._dump_coverage()
        self.__spectra = Spectra.from_coverage(self.__coverage)
        self.__logger.debug("generated coverage spectra: %s", self.__spectra)
        self.__localization = \
            Localization.from_spectra(self.__spectra, suspiciousness_metric)
        self.__logger.debug("transformed spectra to fault localization: %s",
                            self.__localization)
        self.__localization = \
            self.__localization.restricted_to_lines(self.__lines)
        self.__logger.info("removing non-suspicious lines from consideration")
        num_lines_before = len(self.__lines)
        self.__lines = \
            self.__lines.filter(lambda l: self.__localization.score(l) > 0)
        num_lines_after = len(self.__lines)
        num_lines_removed = num_lines_before - num_lines_after
        self.__logger.info("removed %d non-suspicious lines from consideration",
                           num_lines_removed)

        # report implicated lines and files
        self.__logger.info("implicated lines [%d]:\n%s",
                           len(self.__lines), self.__lines)
        self.__logger.info("implicated files [%d]:\n* %s",
                           len(self.__lines.files),
                           '\n* '.join(self.__lines.files))
        if len(self.__lines) == 0:
            raise NoImplicatedLines

        # construct the snippet database from the parts of the program that
        # were executed by the test suite (both passing and failing tests)
        # TODO add a snippet extractor component
        self.__logger.info("constructing snippet database")
        self.__snippets = SnippetDatabase()

        # TODO allow additional snippet filters to be provided as params
        snippet_filters = [
            filters.ends_with_semi_colon,
            filters.has_balanced_delimiters
        ]

        for line in self.__coverage.lines:
            content = self.__sources.line(line.filename, line.num).strip()
            if all(fltr(content) for fltr in snippet_filters):
                # self.__logger.debug("* found snippet at %s: %s", line, content)
                snippet = Snippet(content)
                self.__snippets.add(snippet, origin=line)

        self.__logger.info("construct snippet database: %d snippets",
                           len(self.__snippets))
        for fn in self.__lines.files:
            self.__logger.info("* %d unique snippets in %s",
                               len(list(self.__snippets.in_file(fn))), fn)

        self.__logger.debug("reducing memory footprint by discarding extraneous data")
        self.__coverage.restricted_to_files(self.__lines.files)
        self.__spectra.restricted_to_files(self.__lines.files)
        extraneous_source_fns = \
            set(self.__sources.files) - set(self.__lines.files)
        for fn in extraneous_source_fns:
            self.__sources = self.__sources.without_file(fn)
        self.__logger.debug("finished reducing memory footprint")

    def _dump_coverage(self) -> None:
        self.__logger.debug("[COVERAGE]\n%s\n[/COVERAGE]",
                            indent(str(self.__coverage), 2))

    @property
    def snippets(self) -> SnippetDatabase:
        """
        The snippet database that should be used to generate new code.
        """
        return self.__snippets

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
    def logger(self) -> logging.Logger:
        """
        The logger that should be used to log output for this problem.
        """
        return self.__logger

    @property
    def localization(self) -> Localization:
        """
        The fault localization for this problem is used to encode the relative
        suspiciousness of source code lines.
        """
        return self.__localization

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
    def sources(self) -> SourceFileCollection:
        """
        The source code files for the program under repair.
        """
        return self.__sources

    def check_sanity(self,
                     expected_to_pass: List[TestCase],
                     expected_to_fail: List[TestCase]
                     ) -> bool:
        """

        Parameters:
            expected_to_pass: a list of test cases for the program that are
                expected to pass.
            expected_to_fail: a list o test cases for the program that are
                expected to fail.

        Returns:
            True if the outcomes of the test executions match those that are
            expected by the parameters to this method.

        Raises:
            errors.UnexpectedTestOutcomes: if the outcomes of the program
                under test, observed while computing coverage information for
                the problem, differ from those that were expected.
        """
        # determine passing and failing tests
        self.__logger.debug("sanity checking...")
        raise NotImplementedError
