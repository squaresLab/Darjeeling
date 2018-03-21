from typing import List, Optional, Dict, Iterator
import tempfile
import logging

import bugzoo
from bugzoo.core.fileline import FileLine, FileLineSet
from bugzoo.core.bug import Bug
from bugzoo.core.coverage import ProjectLineCoverage
from bugzoo.core.patch import Patch
from bugzoo.core.coverage import TestSuiteCoverage
from bugzoo.testing import TestCase

from darjeeling.donor import DonorPool
from darjeeling.transformation import TransformationDatabase
from darjeeling.source import SourceFile


class Problem(object):
    """
    Used to provide a description of a problem (i.e., a bug), and to hold
    information pertinent to its solution (e.g., coverage, transformations).
    """
    def __init__(self,
                 bz: bugzoo.BugZoo,
                 bug: Bug,
                 in_files: Optional[List[str]],
                 in_functions: Optional[List[str]] = None,
                 restrict_to_lines: Optional[FileLineSet] = None
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
        """
        assert len(in_files) > 0
        self.__bug = bug

        self.__logger = \
            logging.getLogger('darjeeling.problem').getChild(bug.name)
        self.__logger.setLevel(logging.DEBUG)
        self.__logger.debug("creating problem for bug: %s", bug.name)

        # coverage
        # coverage = bug.coverage.restricted_to_files(in_files) if in_files \
        #            else bug.coverage
        # spectra = bug.spectra.restricted_to_files(in_files) if in_files \
        #           else bug.spectra

        self.__in_files = in_files[:]
        self.__in_functions = in_functions[:] if in_functions else None

        # stores the contents of each original source code file
        self.__logger.debug("storing contents of source code files")
        self.__sources = \
            {fn: SourceFile.load(bz, bug, fn) for fn in self.__in_files}
        self.__logger.debug("finished storing contents of source code files")

        # TODO determine the passing (positive) and failing (negative) tests
        self.__logger.debug("determining passing and failing tests")
        try:
            container_sanity = bz.containers.provision(bug)
            self.__tests_failing = set()
            self.__tests_passing = set()
            for test in bug.tests:
                print("executing test: {}".format(test))
                outcome = bz.containers.execute(container_sanity, test)
                if outcome.passed:
                    self.__tests_failing.add(test)
                else:
                    self.__tests_passing.add(test)

        finally:
            del bz.containers[container_sanity.uid]

        self.__logger.debug("determined passing and failing tests")
        self.__logger.debug("- passing tests: %s", ' '.join([t.name for t in self.__tests_passing]))
        self.__logger.debug("- failing tests: %s", ' '.join([t.name for t in self.__tests_failing]))

        # determine the implicated lines
        self.__lines = []
        for (fn, src) in self.__sources.items():
            for (num, content) in enumerate(src, 1):
                line = FileLine(fn, num)
                self.__lines.append(line)

        self.__lines = FileLineSet.from_list(lines)
        if restrict_to_lines is not None:
            self.__lines = self.__lines.intersection(restrict_to_lines)

        # construct the donor pool
        self.__logger.debug("constructing donor pool")
        self.__snippets = DonorPool.from_files(bz, bug, in_files)
        self.__logger.debug("constructed donor pool")

        # construct the transformation database
        self.__transformations = \
            TransformationDatabase.generate(bug,
                                            self.__snippets,
                                            self.__sources,
                                            self.__lines)

    @property
    def bug(self) -> Bug:
        """
        A description of the bug, provided by BugZoo.
        """
        return self.__bug

    @property
    def transformations(self) -> TransformationDatabase:
        return self.__transformations

    @property
    def tests(self) -> Iterator[TestCase]:
        return self.bug.tests

    @property
    def coverage(self) -> TestSuiteCoverage:
        """
        Line coverage information for each test within the test suite for the
        program under repair.
        """
        raise NotImplementedError

    @property
    def implicated_lines(self) -> Iterator[FileLine]:
        return self.__lines.__iter()

    def source(self, fn: str) -> SourceFile:
        """
        Returns the contents of a given source code file for this problem.
        """
        return self.__sources[fn]
