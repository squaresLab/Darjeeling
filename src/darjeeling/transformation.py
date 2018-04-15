from typing import List, Iterator, Dict

from bugzoo.core.bug import Bug
from bugzoo.core.fileline import FileLine
from bugzoo.core.filechar import FileCharRange

from .snippet import Snippet
from .source import SourceFile


class Transformation(object):
    @property
    def diff(self) -> str:
        raise NotImplementedError


class CharRangeTransformation(Transformation):
    def __init__(self, char_range: FileCharRange) -> None:
        self.__char_range = char_range

    @property
    def char_range(self) -> FileCharRange:
        return self.__char_range


class DeleteTransformation(CharRangeTransformation):
    def __str__(self) -> str:
        return "DELETE[{}]".format(self.char_range)


class ReplaceTransformation(CharRangeTransformation):
    """
    Replaces a numbered line in a given file with a provided snippet.
    """
    def __init__(self, char_range: FileCharRange, snippet: Snippet) -> None:
        super().__init__(char_range)
        self.__snippet = snippet

    @property
    def snippet(self) -> Snippet:
        return self.__snippet

    def __str__(self) -> str:
        return "REPLACE[{}; {}]".format(self.char_range, self.__snippet)


class AppendTransformation(CharRangeTransformation):
    """
    Appends a given snippet to a specific line in a given file.
    """
    def __init__(self, char_range: FileCharRange, snippet: Snippet) -> None:
        super().__init__(char_range)
        self.__snippet = snippet

    @property
    def snippet(self) -> Snippet:
        return self.__snippet

    def __str__(self) -> str:
        return "APPEND[{}; {}]".format(self.char_range, self.__snippet)
