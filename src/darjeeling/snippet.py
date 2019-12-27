# -*- coding: utf-8 -*-
__all__ = ('Snippet', 'SnippetDatabase',
           'LineSnippet', 'LineSnippetDatabase',
           'StatementSnippet', 'StatementSnippetDatabase')

from typing import (List, Iterator, Set, Optional, Dict, Generic,
                    Any, FrozenSet, MutableSet, TypeVar, Collection)
from collections import OrderedDict
import abc
import logging
import typing

import attr
from kaskara import Statement as KaskaraStatement
from kaskara.analysis import Analysis as KaskaraAnalysis

from .core import FileLocationRange, FileLine, FileLineSet

if typing.TYPE_CHECKING:
    from .config import Config
    from .problem import Problem

logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

T = TypeVar('T', bound='Snippet')


class Snippet(abc.ABC):
    """A snippet of code that may be inserted into a program."""
    @property
    @abc.abstractmethod
    def content(self) -> str:
        ...

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, Snippet):
            return False
        return self.content < other.content
    
    def __str__(self) -> str:
        return self.content
    
    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Snippet) and self.content == other.content
    
    def __hash__(self) -> int:
        return hash(self.content)


@attr.s(slots=True, frozen=True, eq=False, hash=False, str=False, auto_attribs=True)
class LineSnippet(Snippet):
    content: str


@attr.s(slots=True, frozen=True, eq=False, hash=False, str=False, auto_attribs=True)
class StatementSnippet(Snippet):
    """A snippet of code that may be inserted into a program."""
    content: str
    kind: Optional[str]
    reads: FrozenSet[str]
    writes: FrozenSet[str]
    declares: FrozenSet[str]
    requires_syntax: FrozenSet[str]

    @property
    def requires_break(self) -> bool:
        return 'break' in self.requires_syntax

    @property
    def requires_continue(self) -> bool:
        return 'continue' in self.requires_syntax

    @property
    def uses(self) -> FrozenSet[str]:
        """The names of the variables used by this snippet."""
        return self.reads | self.writes


class SnippetDatabase(Generic[T], Collection[T], abc.ABC):
    def __init__(self) -> None:
        """Constructs an empty snippet database."""
        self.__content_to_snippet: OrderedDict[str, T] = OrderedDict()
        self.__filename_to_snippets: Dict[str, MutableSet[T]] = {}
        self.__content_to_lines: Dict[str, MutableSet[FileLine]] = \
            OrderedDict()

    def __iter__(self) -> Iterator[T]:
        """Returns an iterator over the snippets in this database."""
        yield from self.__content_to_snippet.values()

    def __len__(self) -> int:
        """Determines the number of snippets in this database."""
        return len(self.__content_to_snippet)

    def __contains__(self, snippet: Any) -> bool:
        """Determines whether a given snippet exists within this database."""
        return snippet.content in self.__content_to_snippet

    def in_file(self, filename: str) -> Iterator[T]:
        """Returns an iterator over all snippets in a given file."""
        yield from self.__filename_to_snippets.get(filename, [])

    def lines_for_snippet(self, snippet: Snippet) -> Iterator[FileLine]:
        """Returns an iterator over all lines at which a snippet appears."""
        yield from self.__content_to_lines.get(snippet.content, [])

    def __index_snippet_by_file(self,
                                snippet: T,
                                filename: str
                                ) -> None:
        if filename not in self.__filename_to_snippets:
            self.__filename_to_snippets[filename] = set()
        self.__filename_to_snippets[filename].add(snippet)

    def __record_snippet_location(self,
                                  snippet: T,
                                  location: FileLocationRange
                                  ) -> None:
        content = snippet.content
        line = FileLine(location.filename, location.start.line)
        if content not in self.__content_to_lines:
            self.__content_to_lines[content] = set()
        self.__content_to_lines[content].add(line)

    def add(self,
            snippet: T,
            location: Optional[FileLocationRange] = None
            ) -> None:
        """Adds a snippet to this database.
        
        Parameters
        ----------
        snippet: T
            The snippet to be added to the database.
        location: FileLocationRange, optional
            The location in the code at which the snippet was found.
        """
        content = snippet.content
        if not content in self.__content_to_snippet:
            self.__content_to_snippet[content] = snippet
        else:
            snippet = self.__content_to_snippet[content]

        if location is not None:
            self.__index_snippet_by_file(snippet, location.filename)
            self.__record_snippet_location(snippet, location)


class StatementSnippetDatabase(SnippetDatabase[StatementSnippet]):
    @staticmethod
    def from_kaskara(analysis: KaskaraAnalysis,
                     config: 'Config'
                     ) -> 'StatementSnippetDatabase':
        logger.debug("constructing snippet database from statements")
        use_canonical_form = \
            config.optimizations.ignore_string_equivalent_snippets
        db = StatementSnippetDatabase()
        for stmt in analysis.statements:
            content = stmt.canonical if use_canonical_form else stmt.content
            if stmt.requires_syntax:
                requires_syntax = frozenset(stmt.requires_syntax)
            else:
                requires_syntax = frozenset()

            snippet = StatementSnippet(
                content=content,
                kind=stmt.kind,
                reads=frozenset(stmt.reads if stmt.reads else []),
                writes=frozenset(stmt.writes if stmt.writes else []),
                declares=frozenset(stmt.declares if stmt.declares else []),
                requires_syntax=requires_syntax)
            db.add(snippet, stmt.location)

        logger.debug("constructed snippet database from snippets")
        logger.debug("snippets:\n%s",
                     '\n'.join([f' * {s.content}' for s in db]))
        return db


class LineSnippetDatabase(SnippetDatabase[LineSnippet]):
    @staticmethod
    def for_problem(problem: 'Problem') -> 'LineSnippetDatabase':
        logger.debug('constructing line snippet database')
        db = LineSnippetDatabase()
        logger.debug('constructed database of %d line snippets', len(db))
        return db
