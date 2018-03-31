from typing import Iterator, List, Iterable

from bugzoo.core.fileline import FileLine

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
    def __init__(self, lines: Iterable[FileLine]) -> None:
        pass


class AppendGenerator(CandidateGenerator):
    def __init__(self) -> None:
        pass
