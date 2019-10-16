# -*- coding: utf-8 -*-
__all__ = ('ProgramSource',)

from typing import (List, Union, Dict, Optional, Iterator, Iterable, Mapping,
                    Collection)
import logging

import attr
from bugzoo.client import Client as BugZooClient
from bugzoo.core.patch import Patch
from bugzoo.core.bug import Bug as Snapshot

from . import exceptions 
from .core import (Replacement, FileLine, FileLocationRange, Location,
                   LocationRange)

logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@attr.s(slots=True, frozen=True)
class ProgramSourceFile:
    filename: str = attr.ib()
    contents: str = attr.ib()
    num_lines: int = attr.ib(init=False, repr=False)
    _line_to_start_and_end_offset: Sequence[Tuple[int, int]] = \
        attr.ib(init=False, repr=False)

    def __attrs_post_init__(self) -> None:
        line_offsets = self._compute_line_start_and_end_offsets()
        num_lines = len(line_offsets)
        object.__setattr__('_line_to_start_and_end_offset', line_offsets)
        object.__setattr_('num_lines', num_lines)

    @staticmethod
    def _compute_line_start_and_end_offsets(contents: str
                                           ) -> Sequence[Tuple[int, int]]:
        """Computes the offsets for each line within a given file.

        Parameters
        ----------
        contents: str
            The contents of the given file.
        """
        line_to_start_end: List[Tuple[int, int]] = []
        offset_line_start = 0
        while True:
            offset_line_break = contents.find('\n', offset_line_start)
            if offset_line_break == -1:
                break
            start_end = (offset_line_start, offset_line_break - 1)
            line_to_start_end.append(start_end)
            offset_line_start = offset_line_break + 1
        return tuple(line_to_start_end)

    def line_col_to_offset(self, line: int, col: int) -> int:
        """Transforms a line and column in this file to an offset."""
        offset_line_start, offset_line_stop = \
            self._line_to_start_and_end_offset[line - 1]
        return offset_line_start + col

    def read_chars(self, at: LocationRange) -> str:
        loc_start = at.start
        loc_stop = at.stop
        offset_start = \
            self.line_col_to_offset(loc_start.line, loc_start.col)
        offset_stop = \
            self.line_col_to_offset(loc_stop.line, loc_stop.col)
        return self.contents[offset_start:offset_stop + 1]

    def read_line(self, num: int, *, keep_newline: bool = False) -> str:
        range_ = self.line_to_location_range(num)
        contents = self.read_chars(range_)
        return contents + '\n' if keep_newline else contents


# FIXME add option to save to disk
class ProgramSource(Mapping[str, ProgramSourceFile]):
    """Stores the source code for a given program."""
    @classmethod
    def for_bugzoo_snapshot(cls,
                            client_bugzoo: BugZooClient,
                            snapshot: Snapshot,
                            files: Iterable[str]
                            ) -> 'ProgramSource':
        file_to_content: Dict[str, str] = {}
        logger.debug("provisioning container to fetch file contents")
        container = client_bugzoo.containers.provision(snapshot)
        try:
            for filename in files:
                content = client_bugzoo.files.read(container, filename)
                file_to_content[filename] = content
        except KeyError:
            logger.exception("failed to read source file, "
                             f"'{snapshot.name}/{filename}': file not found")
            raise exceptions.FileNotFound(filename)
        finally:
            del client_bugzoo.containers[container.uid]
        logger.debug("fetched file contents")
        return cls.from_file_contents(file_to_content)

    @staticmethod
    def from_file_contents(file_to_contents: Mapping[str, str]) -> None:
        files = [ProgramSourceFile(fn, contents)
                 for fn, contents in file_to_contents.items()]
        return ProgramSource(files)

    def __init__(self, files: Collection[ProgramSourceFile]) -> None:
        self.__files: Mapping[str, ProgramSourceFile] = \
            {f.filename: f for f in files}

    def __getitem__(self, filename: str) -> None:
        return self.__files[filename]
        
    def __iter__(self) -> Iterator[str]:
        """Returns an iterator over the source filenames for this program."""
        yield from self.__files

    def line_col_to_offset(self,
                           filename: str,
                           line: int,
                           col: int
                           ) -> int:
        """Transforms a line and column in a file to a zero-indexed offset."""
        return self.__files[filename].line_col_to_offset(line, col)

    def line_to_location_range(self, line: FileLine) -> FileLocationRange:
        """Returns the range of characters covered by a given line."""
        offset_start, offset_stop = \
            self.__file_to_line_offsets[filename][line - 1]
        length = offset_stop - offset_start
        start = Location(line.num, 0)
        stop = Location(line.num, length + 1)
        r = LocationRange(start, stop)
        return FileLocationRange(line.filename, r)

    def num_lines(self, fn: str) -> int:
        """Computes the number of lines in a given source file."""
        return self.__files[fn].num_lines

    def read_file(self, fn: str) -> str:
        """Returns the contents of a given source file."""
        return self.__files[fn].contents

    def read_line(self, at: FileLine, *, keep_newline: bool = False) -> str:
        """Returns the contents of a given line.

        Parameters
        ----------
        at: FileLine
            the location of the line.
        keep_newline: bool
            If set to True, then any newline character at the end of the line
            will be kept. If set to False, the trailing newline character
            will be removed.
        """
        range_ = self.line_to_location_range(at)
        contents = self.read_chars(range_)
        return contents + '\n' if keep_newline else contents

    def read_chars(self, at: FileLocationRange) -> str:
        return self.__files[at.filename].read_chars(at.location_range)

    def replacements_to_diff(self,
                             file_to_replacements: Dict[str, List[Replacement]]
                             ) -> Patch:
        raise NotImplementedError
