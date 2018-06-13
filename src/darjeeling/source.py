__all__ = ['ProgramSourceManager']

from typing import List, Union, Dict, Optional, Iterator, Iterable

import boggart
from rooibos import Client as RooibosClient
from bugzoo.client import Client as BugZooClient
from bugzoo.core.patch import Patch
from bugzoo.core.bug import Bug as Snapshot

from .core import Replacement, FileLine, FileLocationRange, Location


# FIXME add option to save to disk
class ProgramSourceManager(object):
    def __init__(self,
                 client_bugzoo: BugZooClient,
                 client_rooibos: Optional[RooibosClient],
                 snapshot: Snapshot,
                 files: Iterable[str]
                 ) -> None:
        # FIXME hacko
        self.__snapshot = snapshot
        SFM = boggart.server.sourcefile.SourceFileManager
        self.__mgr = SFM(client_bugzoo,
                         client_rooibos,
                         boggart.config.Operators())  # type: ignore  # noqa: pycodestyle
        self.__files = list(files)
        self.__mgr._fetch_files(snapshot, self.__files)
        for fn in files:
            self.__mgr.read_file(snapshot, fn)

    @property
    def files(self) -> Iterator[str]:
        yield from self.__files

    # FIXME move to boggart
    def line_to_location_range(self, line: FileLine) -> FileLocationRange:
        """
        Returns the range of characters that are covered by a given line.
        """
        content = self.__mgr.read_line(self.__snapshot, line)  # TODO include newline?
        return FileLocationRange(line.filename,
                                 Location(line.num, 0),
                                 Location(line.num, len(content)))

    def num_lines(self, fn: str) -> int:
        """
        Computes the number of lines in a given source file.
        """
        return self.__mgr.num_lines(self.__snapshot, fn)

    def read_file(self, fn: str) -> str:
        """
        Returns the contents of a given source file.
        """
        return self.__mgr.read_file(self.__snapshot, fn)

    def read_line(self, at: FileLine, *, keep_newline: bool = False) -> str:
        """
        Returns the contents of a given line.

        Parameters:
            at: the location of the line.
            keep_newline: if set to True, then any newline character at the
                end of the line will be kept. If set to False, the trailing
                newline character will be removed.
        """
        content = self.__mgr.read_line(self.__snapshot, at)
        return content.rstrip('\n') if keep_newline else content

    def read_chars(self, at: FileLocationRange) -> str:
        return self.__mgr.read_chars(self.__snapshot, at)

    def __delitem__(self, fn: str) -> None:
        """
        Removes information for a given file from this manager.
        """
        self.__files.remove(fn)
        self.__mgr._forget_file(self.__snapshot, fn)

    def replacements_to_diff(self,
                             file_to_replacements: Dict[str, List[Replacement]]
                             ) -> Patch:
        return self.__mgr.replacements_to_diff(self.__snapshot,
                                               file_to_replacements)
