from typing import List, Iterator, Set, Iterable
from tempfile import NamedTemporaryFile
import os
import tempfile

import bugzoo
from bugzoo.core.bug import Bug
from bugzoo.core.coverage import FileLine

from .source import SourceFile


class Snippet(object):
    """
    Represents a donor code snippet.
    """
    def __init__(self, content: str):
        self.__content = content

    @property
    def content(self) -> str:
        """
        Returns the contents of the snippet as a string.
        """
        return self.__content

    def __str__(self) -> str:
        return self.__content

    def __eq__(self, other) -> bool:
        return isinstance(other, Snippet) and self.content == other.content

    def __hash__(self) -> int:
        return hash(self.__content)


class DonorPool(object):
    @staticmethod
    def from_files(bz: bugzoo.BugZoo,
                   bug: Bug,
                   filenames: List[str]
                   ) -> 'DonorPool':
        file_snippets = [DonorPool.from_file(bz, bug, fn) for fn in filenames]
        all_snippets = [s for pool in file_snippets for s in pool]
        return DonorPool(all_snippets)

    @staticmethod
    def from_file(bz: bugzoo.BugZoo,
                  bug: Bug,
                  filename: str
                  ) -> 'DonorPool':
        """
        Constructs a donor pool of snippets from the contents of a given file.
        """
        snippets = set()
        src_file = SourceFile.load(bz, bug, filename)

        # create a snippet for each line
        for content in src_file:
            content = content.strip()

            # skip comments
            if content.startswith('/*') or content.startswith('/'):
                continue

            # skip macros
            if content.startswith('#'):
                continue

            # restrict to statements
            if not content.endswith(';'):
                continue

            snippets.add(Snippet(content))

        return DonorPool(snippets)

    def __init__(self, snippets: Iterable[Snippet]):
        self.__snippets = frozenset(snippets)

    def __iter__(self) -> Iterator[Snippet]:
        """
        Returns an iterator over the snippets contained in this donor pool.
        """
        return self.__snippets.__iter__()
