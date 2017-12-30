from typing import List, Optional, Dict, Iterator
from bugzoo.coverage import FileLine
from bugzoo.bug import Bug
from bugzoo.testing import TestCase
from bugzoo.coverage import ProjectLineCoverage
from darjeeling.donor import DonorPool


class Problem(object):
    """
    Used to provide a description of a problem (i.e., a bug), and to hold
    information pertinent to its solution (e.g., coverage, transformations).
    """
    def __init__(self,
                 bug: Bug,
                 in_files: List[str],
                 in_functions: Optional[List[str]] = None
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

        # - transformation database
        # - coverage
        # - fault localisation?

        # coverage = bug.coverage.restricted_to_files(in_files) if in_files \
        #            else bug.coverage
        # spectra = bug.spectra.restricted_to_files(in_files) if in_files \
        #           else bug.spectra
        self.__in_files = in_files[:] if in_files else None
        self.__in_functions = in_functions[:] if in_functions else None

        # construct the donor pool
        self.__snippets = DonorPool.from_files(bug, in_files)

        # construct the transformation database

    @property
    def bug(self) -> Bug:
        """
        A description of the bug, provided by BugZoo.
        """
        return self.__bug

    @property
    def coverage(self) -> Dict[TestCase, ProjectLineCoverage]:
        """
        Line coverage information for each test within the test suite for the
        program under repair.
        """
        raise NotImplementedError

    @property
    def implicated_lines(self) -> Iterator[FileLine]:
        raise NotImplementedError
