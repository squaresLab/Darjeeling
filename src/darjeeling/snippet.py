from typing import List, Iterator, Set, Iterable, Optional, Dict, Callable
import logging

from bugzoo.core.coverage import FileLine

from .problem import Problem

logger = logging.getLogger(__name__)  # type: logging.Logger


# FIXME use attrs
class Snippet(object):
    """
    Represents a donor code snippet.
    """
    def __init__(self, content: str) -> None:
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
    # TODO: implement load and save functionality (use cPickle)
    @staticmethod
    def from_problem(problem: Problem,
                     filters: Optional[List[Callable[[str], bool]]] = None
                     ) -> 'SnippetDatabase':
        if filters is None:
            filters = []

        logger.info("building snippet database for problem")
        sources = problem.sources
        db = SnippetDatabase()

        for line in problem.lines:
            content = sources.read_line(line).strip()
            if all(f(content) for f in filters):
                snippet = Snippet(content)
                db.add(snippet, origin=line)

        logger.info("built snippet database: %d snippets", len(db))
        return db

    def __init__(self) -> None:
        self.__snippets = set() # type: Set[Snippet]
        self.__snippets_by_file = {} # type: Dict[str, Set[Snippet]]

    def __iter__(self) -> Iterator[Snippet]:
        """
        Returns an iterator over the snippets contained in this databse.
        """
        return self.__snippets.__iter__()

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
        return

    def add(self,
            snippet: Snippet,
            *,
            origin: Optional[FileLine] = None
            ) -> None:
        """
        Adds a snippet to this database in-place.

        Parameters:
            snippet: the snippet to add.
            origin: an optional parameter that may be used to specify the
                origin of the snippet.

        Returns:
            nothing.
        """
        self.__snippets.add(snippet)

        if origin is not None:
            if origin.filename not in self.__snippets_by_file:
                self.__snippets_by_file[origin.filename] = {
                    Snippet('return;'),
                    Snippet('return true;'),
                    Snippet('return false;')
                }
            self.__snippets_by_file[origin.filename].add(snippet)


class SnippetFinder(object):
    def __init__(self, database: SnippetDatabase) -> None:
        self.__database = database

    def __next__(self) -> Iterator[Snippet]:
        return self.__database.__iter__()
