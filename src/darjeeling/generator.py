from typing import Iterator, List, Iterable, Tuple, Optional
import random

from bugzoo.localization import Localization
from bugzoo.core.fileline import FileLine
from bugzoo.core.filechar import FileCharRange

from .problem import Problem
from .snippet import Snippet, SnippetDatabase
from .candidate import Candidate
from .transformation import Transformation, \
                            AppendTransformation, \
                            DeleteTransformation, \
                            ReplaceTransformation


class CandidateGenerator(Iterable):
    """
    Candidate generators are used to generate (normally in a lazy fashion) a
    stream of candidate patches. For now, candidate generators implement
    one-way communications: they do not accept inputs.
    """
    def __iter__(self) -> Iterator[Candidate]:
        return self

    def __next__(self) -> Candidate:
        raise NotImplementedError


class TransformationGenerator(Iterable):
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


class TargetSnippetGenerator(Iterable):
    def __init__(self,
                 targets: Iterator[FileCharRange],
                 snippets: SnippetDatabase
                 ) -> None:
        self.__targets = targets
        self.__snippets = snippets
        self.__current_target = None # type: Optional[FileCharRange]
        self.__snippets_at_target = iter([]) # type: Iterator[Snippet]

    def __iter__(self) -> Iterator[Tuple[FileCharRange, Snippet]]:
        return self

    def __next__(self) -> Tuple[FileCharRange, Snippet]:
        # fetch the next snippet at the current line
        # if there are no snippets left at this line, move onto
        # the next line. if there are no lines left, stop iterating.
        try:
            snippet = next(self.__snippets_at_target)
            return (self.__current_target, snippet)
        except StopIteration:
            try:
                # TODO use snippet generator here
                # - return snippets at current file
                # - add use/def restrictions
                self.__current_target = next(self.__targets)
                self.__snippets_at_target = \
                    self.__snippets.in_file(self.__current_target.filename)
                return self.__next__()
            except StopIteration:
                raise StopIteration


class DeletionGenerator(TransformationGenerator):
    def __init__(self, targets: Iterable[FileCharRange]) -> None:
        """
        Constructs a deletion generator.
        """
        self.__targets = reversed(list(targets))

    def __next__(self) -> Transformation:
        """
        Returns the next deletion transformation from this generator.
        """
        try:
            next_target = next(self.__targets)
        except StopIteration:
            raise StopIteration

        # TODO add static analysis
        # should we delete this line?
        # * don't delete declarations
        return DeleteTransformation(next_target)


class ReplacementGenerator(TransformationGenerator):
    """
    Uses a provided snippet database to generate all legal replacement
    transformations for a sequence of transformation targets.
    """
    def __init__(self,
                 targets: Iterator[FileCharRange],
                 snippets: SnippetDatabase
                 ) -> None:
        self.__generator_target_snippet = \
            TargetSnippetGenerator(targets, snippets)

    def __next__(self) -> Transformation:
        try:
            target, snippet = next(self.__generator_target_snippet)
        except StopIteration:
            raise StopIteration

        # TODO additional static analysis goes here
        # don't replace line with an equivalent

        return ReplaceTransformation(target, snippet)


class AppendGenerator(TransformationGenerator):
    def __init__(self,
                 targets: Iterator[FileCharRange],
                 snippets: SnippetDatabase
                 ) -> None:
        self.__generator_target_snippet = \
            TargetSnippetGenerator(targets, snippets)

    def __next__(self) -> Transformation:
        try:
            target, snippet = next(self.__generator_target_snippet)
        except StopIteration:
            raise StopIteration

        # TODO additional static analysis goes here
        # * don't append after a return
        # * don't append after a break statement

        return AppendTransformation(target, snippet)


class AllTransformationsAtLine(TransformationGenerator):
    """
    Provides a stream of all the possible transformations that can be made at
    a single line using a given snippet database.
    """
    def __init__(self,
                 problem: Problem,
                 line: FileLine,
                 snippets: SnippetDatabase,
                 *,
                 randomize: bool = True
                 ) -> None:
        # transform line to character range
        # TODO tidy this hack
        char_range = problem.sources[line.filename].line_to_char_range(line)

        # TODO clean up iterator ugliness
        self.__sources = [
            DeletionGenerator(iter([char_range])),
            ReplacementGenerator(iter([char_range]), snippets),
            AppendGenerator(iter([char_range]), snippets)
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


# TODO: map from transformation targets to line numbers
class SampleByLocalization(TransformationGenerator):
    def __init__(self,
                 problem: Problem,
                 localization: Localization,
                 snippets: SnippetDatabase,
                 *,
                 randomize: bool = True
                 ) -> None:
        self.__localization = localization
        self.__transformations_by_line = {
            line: AllTransformationsAtLine(problem, line, snippets, randomize=randomize)
            for line in localization
        }

    def __next__(self) -> Transformation:
        try:
            line = self.__localization.sample()
            print("Looking at line: {}".format(line))
            source = self.__transformations_by_line[line]
        except ValueError:
            raise StopIteration

        try:
            return next(source)
        except StopIteration:
            del self.__transformations_by_line[line]
            self.__localization = self.__localization.without_line(line)
            return self.__next__()
