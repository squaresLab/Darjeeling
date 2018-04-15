from typing import List, Iterator
import difflib

from bugzoo.core.patch import FilePatch
from bugzoo.core.fileline import FileLine
from bugzoo.core.filechar import FileCharRange, FileChar


class SourceFile(object):
    def __init__(self, name: str, contents: str) -> None:
        assert isinstance(contents, str)
        assert isinstance(name, str)

        self.__name = name
        self.__contents = contents

        # FIXME this will miss the last line
        line_end_at = -1
        self.__lines = [] # type: List[FileCharRange]
        while True:
            try:
                line_start_at = line_end_at + 1
                line_end_at = contents.index("\n", line_start_at)
            except ValueError:
                break
            char_range = \
                FileCharRange(FileChar(name, line_start_at),
                              FileChar(name, line_end_at))
            self.__lines.append(char_range)

    @property
    def name(self) -> str:
        """
        The name of this source code file.
        """
        return self.__name

    def line_to_char_range(self, line: FileLine) -> FileCharRange:
        return self.__lines[line.num - 1]

#    @property
#    def lines(self) -> Iterator[FileCharRange]:
#        """
#        Returns a list of the character ranges of the lines contained
#        within this file.
#        """
#        return self.__lines.copy()

    def __str__(self) -> str:
        """
        Returns the contents of this file as a string.
        """
        return self.__contents

    def __getitem__(self, char_range: FileCharRange) -> str:
        """
        Returns the source code contained within a given range.
        """
        c_start = char_range.start.offset
        c_end = char_range.stop.offset
        return self.__contents[c_start:c_end + 1]

    def insert(self, index: FileChar, text: str) -> 'SourceFile':
        # FIXME allow insertion rather than simply appending
        contents = "{}\n{}{}".format(self.__contents[:index],
                                     text,
                                     self.__contents[index:])
        return SourceFile(self.name, contents)

    def delete(self, char_range: FileCharRange) -> 'SourceFile':
        """
        Returns a variant of this file without the text contained in a given
        source range.
        """
        return self.replace(char_range, '')

    def replace(self,
                char_range: FileCharRange,
                replacement: str
                ) -> 'SourceFile':
        """
        Returns a variant of this file where the text contained in a given
        source range has been replaced with a given string.
        """
        c_start = char_range.start.offset
        c_stop = char_range.stop.offset
        contents = "{}{}\n{}".format(self.__contents[:c_start],
                                     replacement,
                                     self.__contents[c_stop+1:])
        return SourceFile(self.name, contents)

    def diff(self, other: 'SourceFile') -> str:
        diff_lines = difflib.unified_diff(str(self).splitlines(True),
                                          str(other).splitlines(True),
                                          fromfile=self.name,
                                          tofile=other.name)
        return ''.join(diff_lines)
