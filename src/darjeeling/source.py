from typing import List, Iterator, Dict
import difflib
import tempfile
import logging
import os

from bugzoo import BugZoo
from bugzoo.core.bug import Bug
from bugzoo.core.patch import FilePatch
from bugzoo.core.fileline import FileLine
from bugzoo.core.filechar import FileCharRange, FileChar

from .util import get_file_contents

logger = logging.getLogger(__name__)  # type: logging.Logger


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
        offset = index.offset
        contents = "{}\n{}{}".format(self.__contents[:offset],
                                     text,
                                     self.__contents[offset:])
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
    @staticmethod
    def from_bug(bz: BugZoo,
                 bug: Bug,
                 filenames: List[str]
                 ) -> 'SourceFileCollection':
        logger.debug("loading source files for snapshot: %s", bug.name)
        sources = {} # type: Dict[str, SourceFile]
        ctr = bz.containers.provision(bug)
        try:
            for fn in filenames:
                # fn_ctr = os.path.join(bug.source_dir, fn)
                fn_ctr = fn
                logger.debug("loading source code file [%s] at [%s]",\
                             fn, fn_ctr)
                contents = bz.files.read(ctr, fn_ctr)
                sources[fn] = SourceFile(fn, contents)
        finally:
            del bz.containers[ctr.uid]
        collection = SourceFileCollection(sources)
        logger.debug("loaded source files for snapshot: %s", bug.name)
        return collection

    def __init__(self, contents: Dict[str, SourceFile]) -> None:
        """
        Constructs a new collection of source files.

        Parameters:
            contents: the contents of the collection, given as a dictionary of
                source files indexed by filename.
        """
        self.__contents = contents

    def __iter__(self) -> Iterator[str]:
        """
        Returns an iterator over the names of the files contained within this
        collection.
        """
        yield from self.__contents.keys()

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
        contents_new[index.filename] = \
            self.__contents[index.filename].insert(index, text)
        return SourceFileCollection(contents_new)

    def diff(self, other: 'SourceFileCollection') -> str:
        raise NotImplementedError

    def line(self, fn: str, num: int) -> str:
        """
        Retrieves the contents of a given line in a source code file.
        """
        assert isinstance(num, int)

        line = FileLine(fn, num)
        f_contents = self.__contents[fn]
        char_range = f_contents.line_to_char_range(line)
        return f_contents[char_range]

    @property
    def files(self) -> List[str]:
        """
        The names of the files that are represented in this collection.
        """
        return [fn for fn in self.__contents]

    def without_file(self, fn: str) -> 'SourceFileCollection':
        """
        Produces a variant of this collection of source files that does not
        contain a file with the given name. If the named file does not exist
        within this collection, then this collection is returned.

        Parameters:
            fn: the name of the file that should not appear in the variant of
                this collection of files.

        Returns:
            a variant of this file collection that does not contain a file with
            the given name.
        """
        if fn not in self.__contents:
            return self

        contents_new = self.__contents.copy()
        return SourceFileCollection(contents_new)
