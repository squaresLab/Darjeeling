from typing import Iterator, List, Iterable

from bugzoo.core.fileline import FileLine

from .snippet import Snippet
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
    def __init__(self) -> Iterator[Candidate]:
        return self

    def __next__(self) -> Candidate:
        raise NotImplementedError


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
    Uses a provided donor pool of code snippets to generate all legal
    replacement transformations for a stream of transformation targets.
    """
    def __init__(self, lines: Iterable[FileLine]) -> None:
        self.__lines = reversed(list(lines))
        self.__current_line = None # type: Optional[FileLine]
        self.__snippets_at_line = iter([]) # type: Iterable[Snippet]

    def __next__(self) -> Candidate:
        # fetch the next snippet at the current line
        # if there are no snippets left at this line, move onto
        # the next line. if there are no lines left, stop iterating.
        try:
            next_snippet = next(self.__snippets_at_line)
        except StopIteration:
            try:
                # TODO use snippet generator here
                # - return snippets at current file
                # - add use/def restrictions
                self.__current_line = next(self.__lines)
                snippets = [
                    'return;',
                    'break;'
                ]
                snippets = [Snippet(s) for s in snippets]
                self.__snippets_at_line = iter(snippets)
                return self.__next__()
            except StopIteration:
                raise StopIteration

        # TODO additional static analysis goes here

        # construct the transformation
        transformation = ReplaceTransformation(self.__current_line,
                                               next_snippet)
        return Candidate([transformation])


class AppendGenerator(CandidateGenerator):
    def __init__(self) -> None:
        pass
