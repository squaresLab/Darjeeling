# -*- coding: utf-8 -*-
__all__ = ('ProgramSource',)

from typing import List, Union, Dict, Optional, Iterator, Iterable, Mapping
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


# FIXME add option to save to disk
class ProgramSource(Mapping[str, ProgramSourceFile]):
    """Stores the source code for a given program."""
    @staticmethod
    def for_bugzoo_snapshot(client_bugzoo: BugZooClient,
                            snapshot: Snapshot,
                            files: Iterable[str]
                            ) -> 'ProgramSource':
        # load the content of each file
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

    def __init__(self, file_to_content: Mapping[str, str]) -> None:
        self.__file_to_content: Mapping[str, str] = dict(file_to_content)
        self.__file_to_line_offsets: Mapping[str, Sequence[Tuple[int, int]]] = \
            {fn: self._compute_line_offsets(content)
             for fn, content in self.__file_to_content}

    @staticmethod
    def _compute_line_offsets(contents: str) -> Sequence[Tuple[int, int]]:
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
        return line_to_start_end

    @property
    def files(self) -> Iterator[str]:
        """Returns an iterator over the source files for this program."""
        yield from self.__file_to_content

    def line_col_to_offset(self,
                           filename: str,
                           line: int,
                           col: int
                           ) -> int:
        """Transforms a line and column in a file to a zero-indexed offset."""
        offset_line_start, offset_line_stop = \
            self.__file_to_line_offsets[filename][line - 1]
        return offset_line_start + col

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
        return len(self.__file_to_content[fn])

    def read_file(self, fn: str) -> str:
        """Returns the contents of a given source file."""
        return self.__file_to_content[fn]

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
        content = self.read_chars(range_)
        return content + '\n' if keep_newline else content

    def read_chars(self, at: FileLocationRange) -> str:
        filename = at.filename
        loc_start = at.start
        loc_stop = at.stop
        offset_start = \
            self.line_col_to_offset(filename, loc_start.line, loc_start.col)
        offset_stop = \
            self.line_col_to_offset(filename, loc_stop.line, loc_stop.col)
        return self.__file_to_content[fn][offset_start:offset_stop + 1]

    def replacements_to_diff(self,
                             file_to_replacements: Dict[str, List[Replacement]]
                             ) -> Patch:
        raise NotImplementedError
