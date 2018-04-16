from typing import Dict, Tuple


class Edit(object):
    pass


class Delete(Edit):
    pass


# need to be able to generate a patch from a sequence of replacements
# * add a swanky source file manager
# * use source files
# * generate a diff from two files

class Replace(Edit):
    def __init__(self,
                 at: FileCharRange,
                 replacement: str
                 ) -> None:
        self.__at = at
        self.__replacement = replacement

    @property
    def at(self) -> FileCharRange:
        """
        The range of characters in a given file that should be replaced by
        this edit.
        """
        return self.__at

    @property
    def replacement(self) -> str:
        """
        The replacement source code.
        """
        return self.__replacement


class Replacements(object):
    def __init__(self,
                 replacements: Iterable[Replace]
                 ) -> None:
        self.__replacements = list(replacements)

    def diff(self, sources) -> Patch:
        x
        return


class Match(object):
    def __init__(self,
                 location: FileCharRange,
                 environment: Dict[str, Tuple[FileCharRange, str]]
                 ) -> None:
        self.__location = location
        self.__environment = environment

    @property
    def location(self):
        """
        The character range over which the template was matched.
        """
        return self.__location

    @property
    def environment(self) -> Dict[str, Tuple[FileCharRange, str]]:
        """
        A mapping from template variables to regions of the source code,
        given as (location, content) pairs.
        """
        return self.__environment.copy()


def matches(tpl: str) -> Iterator[Match]:
    return


def rewrite():
    # given a match and a rewrite template
    # given an environment
    # we could check the environment against the rewrite template


class MatchGenerator(object):
    def __init__(self):
        pass

    def __iter__(self) -> 'MatchGenerator':
        return self

    def __next__(self) -> 'Match':
        pass
