from typing import List, Optional
from bugzoo.bug import Bug


class Problem(object):
    """
    Used to provide a description of a problem (i.e., a bug), and to hold
    information pertinent to its solution (e.g., coverage, transformations).
    """
    def __init__(self,
                 bug: Bug,
                 in_files: Optional[List[str]] = None,
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
        # - transformation database
        # - coverage
        # - fault localisation?

        self.__in_files = in_files[:] if in_files else None
        self.__in_functions = in_functions[:] if in_functions else None

        # program (named bug, Docker image, or given as source code)
        self.__bug = None

    @property
    def bug(self) -> Bug:
        """
        A description of the bug, provided by BugZoo.
        """
        return self.__bug
