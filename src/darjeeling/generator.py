from typing import Iterator, List, Iterable, Tuple

from bugzoo.core.fileline import FileLine

from .snippet import Snippet, SnippetDatabase
from .candidate import Candidate
from .transformation import Transformation, \
                            AppendTransformation, \
                            DeleteTransformation, \
                            ReplaceTransformation


class CandidateGenerator(object):
    """
    Candidate generators are used to generate (normally in a lazy fashion) a
    stream of candidate patches. For now, candidate generators implement
    one-way communications: they do not accept inputs.
    """
    def __iter__(self) -> Iterator[Candidate]:
        return self

    def __next__(self) -> Candidate:
        raise NotImplementedError


class LineSnippetGenerator(object):
    def __init__(self,
                 lines: Iterable[FileLine],
                 snippets: SnippetDatabase
                 ) -> None:
        self.__lines = lines
        self.__snippets = snippets
        self.__current_line = None # type: Optional[FileLine]
        self.__snippets_at_line = iter([]) # type: Iterable[Snippet]

    def __next__(self) -> Tuple[FileLine, Snippet]:
        # fetch the next snippet at the current line
        # if there are no snippets left at this line, move onto
        # the next line. if there are no lines left, stop iterating.
        try:
            snippet = next(self.__snippets_at_line)
            return (self.__current_line, snippet)
        except StopIteration:
            try:
                # TODO use snippet generator here
                # - return snippets at current file
                # - add use/def restrictions
                self.__current_line = next(self.__lines)
                self.__snippets_at_line = \
                    self.__snippets.__iter__()
                return self.__next__()
            except StopIteration:
                raise StopIteration


class DeletionGenerator(CandidateGenerator):
    def __init__(self, lines: Iterable[FileLine]) -> None:
        """
        Constructs a deletion generator.

        Parameters:
            lines: a sequence of lines for which deletion transformations
                should be generated.
        """
        self.__lines = reversed(list(lines))

    def __next__(self) -> Candidate:
        """
        Returns the next deletion transformation from this generator.
        """
        try:
            next_line = next(self.__lines)
        except StopIteration:
            raise StopIteration

        # TODO add static analysis
        # should we delete this line?
        # * don't delete declarations

        transformation = DeleteTransformation(next_line)
        return Candidate([transformation])


class ReplacementGenerator(CandidateGenerator):
    """
    Uses a provided snippet database to generate all legal replacement
    transformations for a sequence of transformation targets.
    """
    def __init__(self,
                 lines: Iterable[FileLine],
                 snippets: SnippetDatabase
                 ) -> None:
        self.__generator_line_snippet = \
            LineSnippetGenerator(lines, snippets)

    def __next__(self) -> Candidate:
        try:
            line, snippet = next(self.__generator_line_snippet)
        except StopIteration:
            raise StopIteration

        # TODO additional static analysis goes here
        # don't replace line with an equivalent

        transformation = ReplaceTransformation(line, snippet)
        return Candidate([transformation])


class AppendGenerator(CandidateGenerator):
    def __init__(self) -> None:
        pass
