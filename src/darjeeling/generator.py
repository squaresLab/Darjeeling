"""
This module provides a number of composable methods for generating code
transformations and candidate patches.
"""
from typing import Iterator, List, Iterable, Tuple, Optional, Type, Dict
import random
import logging
import yaml

from rooibos import Client as RooibosClient
from rooibos import Match

from .localization import Localization
from .exceptions import NoImplicatedLines
from .core import FileLocationRange, FileLine, Location
from .problem import Problem
from .snippet import Snippet, SnippetDatabase
from .candidate import Candidate
from .transformation import Transformation, \
                            RooibosTransformation, \
                            AppendTransformation, \
                            DeleteTransformation, \
                            ReplaceTransformation

logger = logging.getLogger(__name__)


class Context(object):
    pass
    # provide access to files


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
    """
    Transformation generators are used to provide a stream of source code
    transformations. As with candidate generators, transformations are usually
    generated in a lazy fashion.
    """
    def __iter__(self) -> Iterator[Transformation]:
        return self

    def __next__(self) -> Transformation:
        raise NotImplementedError


class RooibosGenerator(TransformationGenerator):
    def __init__(self,
                 problem: Problem,
                 localization: Localization,
                 schemas: List[Type[RooibosTransformation]]
                 ) -> None:
        client_rooibos = problem.rooibos
        self.__problem = problem
        size = 0
        tally_by_file = \
            {fn: 0 for fn in localization.files}  # type: Dict[str, int]
        tally_by_schema = \
            {s: 0 for s in schemas}  # type: Dict[Type[RooibosTransformation], int]  # noqa: pycodestyle
        self.__localization = localization
        self.__transformations = \
            {l: {s: [] for s in schemas} for l in localization}  # type: Dict[FileLine, Dict[Type[RooibosTransformation], List[Transformation]]]  # noqa: pycodestyle

        logger.debug("computing transformations")
        for fn in localization.files:
            file_contents = problem.sources.read_file(fn)
            for schema in schemas:
                logger.debug("finding matches of %s in %s", schema.__name__, fn)
                tpl_match = schema.match
                matches = client_rooibos.matches(file_contents, tpl_match)
                for m in matches:
                    line = FileLine(fn, m.location.start.line)
                    if line not in localization:
                        continue
                    if not schema.is_valid_match(m):
                        logger.debug("skipping invalid match: %s", m)
                        continue
                    transformations = \
                        list(self._match_to_transformations(fn, schema, m))
                    size += len(transformations)
                    tally_by_schema[schema] += len(transformations)
                    tally_by_file[fn] += len(transformations)
                    self.__transformations[line][schema] += transformations

        # trim redundant parts of transformation map
        for line in localization:
            for schema in schemas:
                if not self.__transformations[line][schema]:
                    del self.__transformations[line][schema]
            if not self.__transformations[line]:
                del self.__transformations[line]

        # refine the fault localization to only cover represented lines
        lines = list(self.__transformations.keys())
        self.__localization = self.__localization.restricted_to_lines(lines)
        logger.info("finished computing transformations: %d transformations across %d lines",  # noqa: pycodestyle
                    size, len(self.__transformations))
        logger.info("transformations: %s", self.__transformations)
        logger.info('tranformations by schema:\n%s',
                    '\n'.join(['  * {}: {}'.format(s.__name__, count)
                               for (s, count) in tally_by_schema.items()]))
        logger.info('tranformations by file:\n%s',
            '\n'.join(['  * {}: {}'.format(fn, count)
                       for (fn, count) in tally_by_file.items()]))

    def _match_to_transformations(self,
                                  filename: str,
                                  schema: Type[RooibosTransformation],
                                  match: Match
                                  ) -> List[Transformation]:
        location = FileLocationRange(filename,
                                     Location(match.location.start.line,
                                              match.location.start.col),
                                     Location(match.location.stop.line,
                                              match.location.stop.col))
        return schema.match_to_transformations(self.__problem,
                                               location,
                                               match.environment)

    def __next__(self) -> Transformation:
        line = self.__localization.sample()
        logger.debug("looking for transformation at %s", line)
        operator_to_transformations = self.__transformations[line]

        # choose an operator at random
        # if there are no operator choices, discard this line
        # if no lines remain, we're finished
        try:
            op = random.choice(list(operator_to_transformations.keys()))
            transformations = operator_to_transformations[op]
        except IndexError:
            logger.debug("no transformations left at %s", line)
            del self.__transformations[line]
            try:
                self.__localization = self.__localization.without(line)
            except NoImplicatedLines:
                logger.debug("no transformations left in search space")
                raise StopIteration
            return self.__next__()

        # choose a transformation at random
        # if there are no more transformation choices, discard this operator
        # choice
        try:
            return transformations.pop()
        except IndexError:
            logger.debug("exhausted all %s transformations at %s", op, line)
            del operator_to_transformations[op]
            return self.__next__()


def all_transformations_in_file(
        problem: Problem,
        transformation_cls: Type[RooibosTransformation],
        filename: str
    ) -> Iterator[Transformation]:
    client_rooibos = problem.rooibos
    file_contents = problem.sources.read_file(filename)
    tpl_match = transformation_cls.match
    tpl_rewrite = transformation_cls.rewrite
    matches = client_rooibos.matches(file_contents, tpl_match)
    for m in matches:
        args = {}  # type: Dict[str, str]  # FIXME
        location = FileLocationRange(filename,
                                     Location(m.location.start.line,
                                              m.location.start.col),
                                     Location(m.location.stop.line,
                                              m.location.stop.col))
        yield transformation_cls(location, args)  # type: ignore


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
        return Candidate([transformation])  # type: ignore


class TargetSnippetGenerator(Iterable):
    def __init__(self,
                 targets: Iterator[FileLocationRange],
                 snippets: SnippetDatabase
                 ) -> None:
        self.__targets = targets
        self.__snippets = snippets
        self.__current_target = None # type: Optional[FileLocationRange]
        self.__snippets_at_target = iter([]) # type: Iterator[Snippet]

    def __iter__(self) -> Iterator[Tuple[FileLocationRange, Snippet]]:
        return self

    def __next__(self) -> Tuple[FileLocationRange, Snippet]:
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
    def __init__(self, targets: Iterable[FileLocationRange]) -> None:
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
                 targets: Iterator[FileLocationRange],
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
                 targets: Iterator[FileLocationRange],
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
        char_range = problem.sources.line_to_location_range(line)

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
            self.__localization = self.__localization.without(line)
            return self.__next__()
