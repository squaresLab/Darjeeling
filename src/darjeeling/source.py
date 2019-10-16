# -*- coding: utf-8 -*-
__all__ = ('ProgramSource',)

from typing import List, Union, Dict, Optional, Iterator, Iterable
import logging

from bugzoo.client import Client as BugZooClient
from bugzoo.core.patch import Patch
from bugzoo.core.bug import Bug as Snapshot

from . import exceptions 
from .core import (Replacement, FileLine, FileLocationRange, Location,
                   LocationRange)

logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# FIXME add option to save to disk
class ProgramSource:
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
        self.__file_to_content = dict(file_to_content)

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
        return self.__mgr.line_col_to_offset(self.__snapshot,
                                             filename,
                                             line,
                                             col)

    # FIXME move to boggart
    def line_to_location_range(self, line: FileLine) -> FileLocationRange:
        """Returns the range of characters covered by a given line."""
        content = self.__mgr.read_line(self.__snapshot, line)
        start = Location(line.num, 0)
        stop = Location(line.num, len(content) + 1)
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
        content = self.__mgr.read_line(self.__snapshot, at)
        return content + '\n' if keep_newline else content

    def read_chars(self, at: FileLocationRange) -> str:
        return self.__mgr.read_chars(self.__snapshot, at)

    def replacements_to_diff(self,
                             file_to_replacements: Dict[str, List[Replacement]]
                             ) -> Patch:
        return self.__mgr.replacements_to_diff(self.__snapshot,
                                               file_to_replacements)
