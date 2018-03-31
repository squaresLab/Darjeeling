from typing import List, Iterator, Set, Iterable, Optional
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


class SnippetDatabase(object):
    @staticmethod
    def from_files(bz: bugzoo.BugZoo,
                   bug: Bug,
                   filenames: List[str]
                   ) -> 'SnippetDatabase':
        file_snippets = [SnippetDatabase.from_file(bz, bug, fn) for fn in filenames]
        all_snippets = [s for pool in file_snippets for s in pool]
        return SnippetDatabase(all_snippets)

    @staticmethod
    def from_file(bz: bugzoo.BugZoo,
                  bug: Bug,
                  filename: str
                  ) -> 'SnippetDatabase':
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

        return SnippetDatabase(snippets)

    def __init__(self, snippets: Optional[Iterable[Snippet]] = None) -> None:
        if snippets is None:
            self.__snippets = set()
        else:
            self.__snippets = set(snippets)

    def __iter__(self) -> Iterator[Snippet]:
        """
        Returns an iterator over the snippets contained in this donor pool.
        """
        return self.__snippets.__iter__()


class SnippetFinder(object):
    def __init__(self, database: SnippetDatabase) -> None:
        self.__database = database
