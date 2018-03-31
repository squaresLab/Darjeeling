from typing import List, Iterator, Set, Iterable, Optional

from bugzoo.core.coverage import FileLine


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
    # TODO: implement load and save functionality (use cPickle)

    def __init__(self, snippets: Optional[Iterable[Snippet]] = None) -> None:
        if snippets is None:
            self.__snippets = set()
        else:
            self.__snippets = set(snippets)

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
        # FIXME index by origin


class SnippetFinder(object):
    def __init__(self, database: SnippetDatabase) -> None:
        self.__database = database

    def __next__(self) -> Iterator[Snippet]:
        return self.__database.__iter__()
