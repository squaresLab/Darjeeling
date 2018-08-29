from typing import List, Iterator, Set, Iterable, Optional, Dict, Callable, \
                   Any, FrozenSet
import json
import logging
import attr

from kaskara import Statement

from .core import FileLocationRange
from .problem import Problem

logger = logging.getLogger(__name__)  # type: logging.Logger


class Snippet(object):
    """
    Represents a code snippet that may be inserted into a program under
    repair.
    """
    @staticmethod
    def from_dict(d: Dict[str, Any]) -> 'Snippet':
        content = d['content']
        kind = d.get('kind')
        reads = d.get('reads', [])
        writes = d.get('writes', [])
        snippet = Snippet(content, kind, reads, writes)

        if 'locations' in d:
            for loc_s in d['locations']:
                loc = FileLocationRange.from_string(loc_s)
                snippet.locations.add(loc)
        return snippet

    def __init__(self,
                 content: str,
                 kind: Optional[str] = None,
                 reads: Iterable[str] = [],
                 writes: Iterable[str] = []
                 ) -> None:
        self.__content = content
        self.__kind = kind
        self.reads = frozenset(reads)  # type: FrozenSet[str]
        self.writes = frozenset(writes)  # type: FrozenSet[str]
        self.locations = set()  # type: Set[FileLocationRange]

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Snippet) and self.content == other.content

    def __hash__(self) -> int:
        return hash(self.content)

    @property
    def uses(self) -> FrozenSet[str]:
        """
        Returns the set of variables used by this snippet, given by their
        names.
        """
        return self.reads + self.writes

    @property
    def content(self) -> str:
        return self.__content

    @property
    def kind(self) -> Optional[str]:
        return self.__kind

    @property
    def occurrences(self) -> int:
        return len(self.locations)

    def to_dict(self) -> Dict[str, Any]:
        d = {}  # type: Dict[str, Any]
        d['content'] = self.__content
        if self.locations:
            d['locations'] = [str(l) for l in self.locations]
        if self.kind:
            d['kind'] = self.kind
        if self.reads:
            d['reads'] = [str(r) for r in self.reads]
        if self.writes:
            d['writes'] = [str(w) for w in self.writes]
        return d


class SnippetDatabase(object):
    @staticmethod
    def from_statements(statements: Iterable[Statement]) -> 'SnippetDatabase':
        logger.debug("constructing snippet database from statements")
        db = SnippetDatabase()
        for stmt in statements:
            db.add(stmt.content, origin=stmt.location, reads=stmt.reads)
        logger.debug("constructed snippet database from snippets")
        return db

    @staticmethod
    def from_dict(d: List[Dict[str, Any]]) -> 'SnippetDatabase':
        snippets = [Snippet.from_dict(s) for s in d]
        return SnippetDatabase(snippets)

    @staticmethod
    def from_file(fn: str) -> 'SnippetDatabase':
        logger.debug("loading snippet database from file: %s", fn)
        with open(fn, 'r') as f:
            jsn = json.load(f)
        db = SnippetDatabase.from_dict(jsn)
        logger.debug("loaded snippet database from file: %s (%d snippets)",
                     fn, len(db))
        return db

    def __init__(self,
                 snippets: Optional[Iterable[Snippet]] = None
                 ) -> None:
        """
        Constructs an empty snippet database.
        """
        if snippets is None:
            snippets = []

        self.__snippets = {}  # type: Dict[str, Snippet]
        for snippet in snippets:
            self.__snippets[snippet.content] = snippet

        self.__snippets_by_file = {}  # type: Dict[str, Set[Snippet]]
        for snippet in snippets:
            for location in snippet.locations:
                fn = location.filename
                if fn not in self.__snippets_by_file:
                    self.__snippets_by_file[fn] = set()
                self.__snippets_by_file[fn].add(snippet)

    def __iter__(self) -> Iterator[Snippet]:
        """
        Returns an iterator over the snippets contained in this databse.
        """
        yield from self.__snippets.values()

    def __len__(self) -> int:
        """
        Returns the number of unique snippets contained within the database.
        """
        return len(self.__snippets)

    def in_file(self, fn: str) -> Iterator[Snippet]:
        """
        Returns an iterator over all of the snippets that were sourced from
        a given file.
        """
        if fn in self.__snippets_by_file:
            yield from self.__snippets_by_file[fn]

    def add(self,
            content: str,
            *,
            kind: Optional[str] = None,
            origin: Optional[FileLocationRange] = None,
            reads: Optional[List[str]] = None
            ) -> None:
        """
        Adds a snippet to this database in-place.

        Parameters:
            content: the content of the snippet.
            origin: an optional parameter that may be used to specify the
                origin of the snippet.

        Returns:
            nothing.
        """
        reads = list(reads) if reads else []

        if content in self.__snippets:
            snippet = self.__snippets[content]
        else:
            snippet = Snippet(content, kind, reads)
            self.__snippets[content] = snippet

        if origin is not None:
            snippet.locations.add(origin)
            if origin.filename not in self.__snippets_by_file:
                self.__snippets_by_file[origin.filename] = set()
            self.__snippets_by_file[origin.filename].add(snippet)

    def to_dict(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self]

    def to_file(self, fn: str) -> None:
        logger.debug("saving snippet database to file: %s", fn)
        jsn = self.to_dict()
        with open(fn, 'w') as f:
            json.dump(jsn, f)
        logger.debug("saved snippet database to file: %s", fn)


class SnippetFinder(object):
    def __init__(self, database: SnippetDatabase) -> None:
        self.__database = database

    def __next__(self) -> Iterator[Snippet]:
        yield from self.__database
