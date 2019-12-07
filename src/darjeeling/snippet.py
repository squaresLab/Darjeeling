# -*- coding: utf-8 -*-
__all__ = ('Snippet', 'TextSnippet', 'StatementSnippet', 'SnippetDatabase',
           'StatementSnippetDatabase')

from typing import (List, Iterator, Set, Optional, Dict, Generic,
                    Any, FrozenSet, MutableSet, TypeVar, Collection)
from collections import OrderedDict
import abc
import logging

import attr
from kaskara import Statement as KaskaraStatement
from kaskara.analysis import Analysis as KaskaraAnalysis

from .core import FileLocationRange, FileLine
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

    @property
    @abc.abstractmethod
    def locations(self) -> MutableSet[FileLocationRange]:
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

    @property
    def occurrences(self) -> int:
        return len(self.locations)


@attr.s(slots=True, eq=False, hash=False, str=False, auto_attribs=True)
class StatementSnippet(Snippet):
    """A snippet of code that may be inserted into a program."""
    content: str
    kind: Optional[str]
    reads: FrozenSet[str]
    writes: FrozenSet[str]
    declares: FrozenSet[str]
    requires_syntax: FrozenSet[str]
    locations: MutableSet[FileLocationRange] = attr.ib(factory=set, repr=False)

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

    @property
    def lines(self) -> Iterator[FileLine]:
        """
        Returns an iterator over the file lines at which this snippet has
        been observed.
        """
        for location in self.locations:
            yield FileLine(location.filename, location.start.line)


class SnippetDatabase(Generic[T], Collection[T], abc.ABC):
    def __init__(self) -> None:
        """Constructs an empty snippet database."""
        self.__content_to_snippet: OrderedDict[str, T] = OrderedDict()
        self.__filename_to_snippets: Dict[str, MutableSet[T]] = {}

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

    def __index_snippet(self, snippet: T) -> None:
        index = self.__filename_to_snippets
        for location in snippet.locations:
            filename = location.filename
            if filename not in self.__filename_to_snippets:
                self.__filename_to_snippets[filename] = set()
            self.__filename_to_snippets[filename].add(snippet)

    def add(self, snippet: T) -> None:
        """Adds a snippet to this database."""
        content = snippet.content
        if content in self.__content_to_snippet:
            canonical_snippet = self.__content_to_snippet[content]
            for location in snippet.locations:
                canonical_snippet.locations.add(location)
        else:
            self.__content_to_snippet[content] = snippet
        self.__index_snippet(snippet)


class StatementSnippetDatabase(SnippetDatabase[StatementSnippet]):
    @staticmethod
    def from_kaskara(analysis: KaskaraAnalysis,
                     config: Config
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

            if stmt.location is not None:
                snippet.locations.add(stmt.location)

            db.add(snippet)

        logger.debug("constructed snippet database from snippets")
        logger.debug("snippets:\n%s",
                     '\n'.join([f' * {s.content}' for s in db]))
        return db
