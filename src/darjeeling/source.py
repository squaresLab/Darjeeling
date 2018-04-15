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


class SourceFileCollection(object):
    def __init__(self, contents: Dict[str, SourceFile]):
        """
        Constructs a new collection of source files.

        Parameters:
            contents: the contents of the collection, given as a dictionary of
                source files indexed by filename.
        """
        self.__contents = contents

    def __getitem__(self, fn: str) -> SourceFile:
        """
        Retrieves a file from this collection.

        Parameters:
            fn: the name of the file.

        Returns:
            the requested file.

        Raises:
            KeyError: if no file with the given name exists within this
                collection.
        """
        return self.__contents[fn]

    def delete(self, char_range: FileCharRange) -> 'SourceFileCollection':
        """
        Returns a variant of this collection where the contents of a specified
        character range within one of its files has been removed.

        Parameters:
            char_range: the range of characters that should be removed.

        Returns:
            a variant of this collection with the desired modifications.

        Raises:
            KeyError: if the file described by the character range does not
                belong to this collection.
        """
        contents_new = self.__contents.copy()
        contents_new[char_range.filename] = \
            self.__contents[char_range.filename].delete(char_range)
        return SourceFileCollection(contents_new)

    def replace(self,
                char_range: FileCharRange,
                text: str
                ) -> 'SourceFileCollection':
        """
        Returns a variant of this collection where the contents of a specified
        character range within one of its files have been replaced by a given
        text.

        Parameters:
            char_range: the range of characters that should be replaced.
            text: the text that should be used as a replacement.

        Returns:
            a variant of this collection with the desired modifications.

        Raises:
            KeyError: if the file described by the character range does not
                belong to this collection.
        """
        contents_new = self.__contents.copy()
        contents_new[char_range.filename] = \
            self.__contents[char_range.filename].replace(char_range, text)
        return SourceFileCollection(contents_new)

    def insert(self,
               index: FileChar,
               text: str
               ) -> 'SourceFileCollection':
        """
        Returns a variant of this collection where a given text has been
        inserted immediately after a specified character in one of the files
        belonging to this collection.

        Parameters:
            index: the position of the character after which the given text
                should be inserted;
            text: the text that should be inserted.

        Returns:
            a variant of this collection with the desired modifications.

        Raises:
            KeyError: if the file described by the character range does not
                belong to this collection.
        """
        contents_new = self.__contents.copy()
        contents_new[char_range.filename] = \
            self.__contents[char_range.filename].insert(index, text)
        return SourceFileCollection(contents_new)

    def diff(self, other: 'SourceFileCollection') -> str:
        raise NotImplementedError
