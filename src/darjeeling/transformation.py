from typing import List, Iterator, Dict

from bugzoo.core.bug import Bug
from bugzoo.core.coverage import FileLine

from .snippet import Snippet
from .source import SourceFile


class Transformation(object):
    @property
    def diff(self) -> str:
        raise NotImplementedError


class DeleteTransformation(object):
    def __init__(self, line: FileLine) -> None:
        self.__line = line

    @property
    def line(self) -> FileLine:
        return self.__line

    def __str__(self) -> str:
        return "DELETE[{}]".format(self.__line)


class ReplaceTransformation(object):
    """
    Replaces a numbered line in a given file with a provided snippet.
    """
    def __init__(self, line: FileLine, snippet: Snippet) -> None:
        self.__line = line
        self.__snippet = snippet

    @property
    def line(self) -> FileLine:
        return self.__line

    @property
    def snippet(self) -> Snippet:
        return self.__snippet

    def __str__(self) -> str:
        return "REPLACE[{}; {}]".format(self.__line, self.__snippet)


class AppendTransformation(object):
    """
    Appends a given snippet to a specific line in a given file.
    """
    def __init__(self, line: FileLine, snippet: Snippet) -> None:
        self.__line = line
        self.__snippet = snippet

    @property
    def snippet(self) -> Snippet:
        return self.__snippet

    @property
    def line(self) -> FileLine:
        return self.__line

    def __str__(self) -> str:
        return "APPEND[{}; {}]".format(self.__line, self.__snippet)
