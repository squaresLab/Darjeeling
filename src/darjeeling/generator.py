from typing import Iterator, List, Iterable, Tuple
import random

from bugzoo.localization import Localization
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


class TransformationGenerator(object):
    def __iter__(self) -> Iterator[Transformation]:
        return self

    def __next__(self) -> Transformation:
        raise NotImplementedError


class SingleEditPatches(CandidateGenerator):
    """
    Provides a stream of single-transformation candidate patches composed using
    a provided stream of transformations.
    """
    def __init__(self,
                 transformations: Iterator[Transformation]
                 ) -> None:
        self.__transformations = transformations

    def __next__(self) -> Candidate:
        try:
            transformation = next(self.__transformations)
        except StopIteration:
            raise StopIteration
        return Candidate([transformation])


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
                    self.__snippets.in_file(self.__current_line.filename)
                return self.__next__()
            except StopIteration:
                raise StopIteration


class DeletionGenerator(TransformationGenerator):
    def __init__(self, lines: Iterable[FileLine]) -> None:
        """
        Constructs a deletion generator.

        Parameters:
            lines: a sequence of lines for which deletion transformations
                should be generated.
        """
        self.__lines = reversed(list(lines))

    def __next__(self) -> Transformation:
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
        return DeleteTransformation(next_line)


class ReplacementGenerator(TransformationGenerator):
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

    def __next__(self) -> Transformation:
        try:
            line, snippet = next(self.__generator_line_snippet)
        except StopIteration:
            raise StopIteration

        # TODO additional static analysis goes here
        # don't replace line with an equivalent

        return ReplaceTransformation(line, snippet)


class AppendGenerator(TransformationGenerator):
    def __init__(self,
                 lines: Iterable[FileLine],
                 snippets: SnippetDatabase
                 ) -> None:
        self.__generator_line_snippet = \
            LineSnippetGenerator(lines, snippets)

    def __next__(self) -> Transformation:
        try:
            line, snippet = next(self.__generator_line_snippet)
        except StopIteration:
            raise StopIteration

        # TODO additional static analysis goes here
        # * don't append after a return
        # * don't append after a break statement

        return AppendTransformation(line, snippet)


class AllTransformationsAtLine(TransformationGenerator):
    """
    Provides a stream of all the possible transformations that can be made at
    a single line using a given snippet database.
    """
    def __init__(self,
                 line: FileLine,
                 snippets: SnippetDatabase,
                 *,
                 randomize: bool = True
                 ) -> None:
        # TODO clean up iterator ugliness
        self.__sources = [
            DeletionGenerator(iter([line])),
            ReplacementGenerator(iter([line]), snippets),
            AppendGenerator(iter([line]), snippets)
        ] # type: List[TransformationGenerator]

        # TODO implement randomize

    def __next__(self) -> Transformation:
        # TODO random/deterministic
        # choose a source at random
        try:
            source = random.choice(self.__sources)
        except IndexError:
            raise StopIteration

        # attempt to fetch a transformation from that source
        # if the source is exhausted, discard it and try again
        try:
            return next(source)
        except StopIteration:
            self.__sources.remove(source)
            return self.__next__()


# TODO: exhibits suspicious memory usage
class SampleByLocalization(TransformationGenerator):
    def __init__(self,
                 localization: Localization,
                 snippets: SnippetDatabase,
                 *,
                 randomize: bool = True
                 ) -> None:
        # TODO compute a weighted map using suspiciousness values
        self.__sources = [
            AllTransformationsAtLine(line, snippets, randomize=randomize)
            for line in localization
        ]

    def __next__(self) -> Transformation:
        # TODO use fault localization as distribution
        try:
            source = random.choice(self.__sources)
        except IndexError:
            raise StopIteration

        try:
            return next(source)
        except StopIteration:
            self.__sources.remove(source)
            return self.__next__()
