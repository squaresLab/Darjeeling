"""
This module is responsible for describing concrete transformations to source
code files.
"""
from typing import List, Iterator, Dict, FrozenSet, Tuple, Iterable, Type, \
                   Optional, Any
import re
import logging
import os
import random

import attr
import rooibos
from kaskara import InsertionPoint

from .base import Transformation, register
from .rooibos import RooibosTransformation
from ..exceptions import NoImplicatedLines
from ..localization import Localization
from ..problem import Problem
from ..snippet import Snippet, SnippetDatabase
from ..core import Replacement, FileLine, FileLocationRange, FileLocation, \
                   FileLineSet, Location, LocationRange

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)

REGEX_HOLE = re.compile('(?<=:\[)\w+(?=\])')


def is_single_token(snippet: str) -> bool:
    return ' ' not in snippet


def find_all(problem: Problem,
             lines: List[FileLine],
             snippets: SnippetDatabase,
             schemas: List[Type[Transformation]]
             ) -> Iterator[Transformation]:
    """
    Returns an iterator over the set of all transformations that can be
    performed at a given set of lines using provided schemas and snippets.
    """
    for schema in schemas:
        line_to_trans = schema.all_at_lines(problem, snippets, lines)
        for trans in line_to_trans.values():
            yield from trans


def sample_by_localization_and_type(problem: Problem,
                                    snippets: SnippetDatabase,
                                    localization: Localization,
                                    schemas: List[Type[Transformation]],
                                    *,
                                    eager: bool = False,
                                    randomize: bool = False,
                                    threads: int = 1
                                    ) -> Iterator[Transformation]:
    """
    Returns an iterator that samples transformations at the different lines
    contained within the fault localization in accordance to the probability
    distribution defined by their suspiciousness scores.
    """
    lines = list(localization)  # type: List[FileLine]
    try:
        schema_to_transformations_by_line = {
            s: s.all_at_lines(problem, snippets, lines, threads=threads)
            for s in schemas
        }  # type: Dict[Type[Transformation], Dict[FileLine, Iterator[Transformation]]]  # noqa: pycodestyle
        logger.debug("built schema->line->transformations map")
    except Exception:
        logger.exception("failed to build schema->line->transformations map")
        raise

    try:
        line_to_transformations_by_schema = {
            line: {sc: schema_to_transformations_by_line[sc].get(line, iter([])) for sc in schemas}  # noqa: pycodestyle
            for line in lines
        } # type: Dict[FileLine, Dict[Type[Transformation], Iterator[Transformation]]]  # noqa: pycodestyle
        logger.debug("built line->schema->transformations map")
    except Exception:
        logger.exception("failed to build line->schema->transformations map")
        raise

    if eager:
        logger.info('eagerly computing entire transformation space')
        collect_transformations = {
            line: {sc: list(line_to_transformations_by_schema[line][sc])
                   for sc in schemas}
            for line in lines
        }  # type: Dict[FileLine, Dict[Type[Transformation], List[Transformation]]]
        logger.info('finished eagerly computing entire transformation space')

        # compute stats
        num_transformations_by_line = {
            line: 0 for line in lines
        }  # type: Dict[FileLine, int]
        num_transformations_by_schema = {
            schema: 0 for schema in schemas
        }  # type: Dict[Type[Transformation], int]
        num_transformations_by_file = {}  # type: Dict[str, int]

        for line in lines:
            sc_to_tx = collect_transformations[line]
            for (sc, tx) in sc_to_tx.items():
                num_transformations_by_line[line] += len(tx)
                num_transformations_by_schema[sc] += len(tx)

        num_transformations_by_line = {
            line: num
            for (line, num) in num_transformations_by_line.items() if num > 0
        }

        for (line, num_tx) in num_transformations_by_line.items():
            filename = line.filename
            if filename not in num_transformations_by_file:
                num_transformations_by_file[filename] = 0
            num_transformations_by_file[filename] += num_tx

        num_transformations_total = sum(num_transformations_by_line.values())

        # report stats
        logger.info("# transformations: %d",
                    num_transformations_total)
        logger.debug("# transformations by file:\n%s",
                     "\n".join(['  * {}: {}'.format(fn, num)
                                for (fn, num) in num_transformations_by_file.items()]))  # noqa: pycodestyle
        logger.debug("# transformations by schema:\n%s",
                     "\n".join(['  * {}: {}'.format(sc.__name__, num)
                                for (sc, num) in num_transformations_by_schema.items()]))  # noqa: pycodestyle
        logger.debug("# transformations by line:\n%s",
                     "\n".join(['  * {}: {}'.format(str(line), num)
                                for (line, num) in num_transformations_by_line.items()]))  # noqa: pycodestyle

        # TODO apply optional randomization

        logger.info('constructing transformation stream from precomputed transformations')  # noqa: pycodestyle
        line_to_transformations_by_schema = {
            line: {schema: iter(collect_transformations[line][schema])
                   for schema in schemas}
            for line in lines
        }
        logger.info('constructed transformation stream from precomputed transformations')  # noqa: pycodestyle

    def sample(localization: Localization) -> Iterator[Transformation]:
        while True:
            line = localization.sample()
            logger.debug("finding transformation at line: %s", line)
            transformations_by_schema = line_to_transformations_by_schema[line]

            if not transformations_by_schema:
                logger.debug("no transformations left at %s", line)
                del line_to_transformations_by_schema[line]
                try:
                    localization = localization.without(line)
                except NoImplicatedLines:
                    logger.debug("no transformations left in search space")
                    raise StopIteration
                continue

            schema = random.choice(list(transformations_by_schema.keys()))
            transformations = transformations_by_schema[schema]
            logger.debug("generating transformation using %s at %s",
                         schema.__name__, line)

            # attempt to fetch the next transformation for the line and schema
            # if none are left, we remove the schema choice
            try:
                t = next(transformations)
                logger.debug("sampled transformation: %s", t)
                yield t
            except StopIteration:
                logger.debug("no %s left at %s", schema.__name__, line)
                try:
                    del transformations_by_schema[schema]
                    logger.debug("removed entry for schema %s at line %s",
                             schema.__name__, line)
                except Exception:
                    logger.exception(
                        "failed to remove entry for %s at %s.\nchoices: %s",
                        schema.__name__, line,
                        [s.__name__ for s in transformations_by_schema.keys()])
                    raise

    yield from sample(localization)


@register("InsertStatement")
@attr.s(frozen=True, repr=False)
class InsertStatement(Transformation):
    location = attr.ib(type=FileLocation)
    statement = attr.ib(type=Snippet)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> 'Transformation':
        location = FileLocation.from_string(d['location'])
        statement = Snippet.from_dict(d['snippet'])
        return InsertStatement(location, statement)

    def _to_dict(self) -> Dict[str, Any]:
        return {'location': str(self.location),
                'statement': self.statement.to_dict()}

    def to_replacement(self, problem: Problem) -> Replacement:
        r = FileLocationRange(self.location.filename,
                              LocationRange(self.location.location, self.location.location))
        return Replacement(r, self.statement.content)

    @classmethod
    def all_at_lines(cls,
                     problem: Problem,
                     snippets: SnippetDatabase,
                     lines: List[FileLine],
                     *,
                     threads: int = 1
                     ) -> Dict[FileLine, Iterator[Transformation]]:
        return {line: cls.all_at_line(problem, snippets, line)
                for line in lines}

    @classmethod
    def all_at_line(cls,
                    problem: Problem,
                    snippets: SnippetDatabase,
                    line: FileLine
                    ) -> Iterator[Transformation]:
        """
        Returns an iterator over all of the possible transformations of this
        kind that can be performed at a given line.
        """
        if problem.analysis is None:
            logger.warning("cannot determine statement insertions: no Kaskara analysis found")  # noqa: pycodestyle
            yield from []  # TODO this is redundant?
            return

        points = problem.analysis.insertions.at_line(line)  # type: Iterator[InsertionPoint]  # noqa: pycodestyle
        for point in points:
            yield from cls.all_at_point(problem, snippets, point)

    @classmethod
    def should_insert_at_location(cls,
                                  problem: Problem,
                                  location: FileLocation
                                  ) -> bool:
        """
        Determines whether an insertion of this kind should be made at a given
        location.
        """
        if not problem.analysis:
            return True
        if not problem.analysis.is_inside_function(location):
            return False
        return True

    @classmethod
    def viable_snippets(cls,
                        problem: Problem,
                        snippets: SnippetDatabase,
                        point: InsertionPoint
                        ) -> Iterator[Snippet]:
        """
        Returns an iterator over the set of snippets that can be used as
        viable insertions at a given insertion point.
        """
        filename = point.location.filename
        yield from snippets.in_file(filename)

    @classmethod
    def all_at_point(cls,
                     problem: Problem,
                     snippets: SnippetDatabase,
                     point: InsertionPoint
                     ) -> Iterator[Transformation]:
        """
        Returns an iterator over all of the transformations of this kind that
        can be performed at a given insertion point.
        """
        location = point.location
        if not cls.should_insert_at_location(problem, location):
            return
        viable_snippets = list(cls.viable_snippets(problem, snippets, point))
        # logger.info("VIABLE SNIPPETS AT POINT [%s]: %s",
        #             point, [s.content for s in viable_snippets])
        for snippet in cls.viable_snippets(problem, snippets, point):
            if snippet.reads.issubset(point.visible):
                yield cls(location, snippet)
            # else:
            #     logger.debug("skipping snippet [%s]: failed scope analysis.",
            #                  snippet.content)

    def __repr__(self) -> str:
        s = "InsertStatement[{}]<{}>"
        s = s.format(str(self.location), str(self.statement.content))
        return s


class InsertVoidFunctionCall(InsertStatement):
    @classmethod
    def viable_snippets(cls,
                        problem: Problem,
                        snippets: SnippetDatabase,
                        point: InsertionPoint
                        ) -> Iterator[Snippet]:
        for snippet in super().viable_snippets(problem, snippets, point):
            if snippet.kind == 'void-call':
                yield snippet


class InsertConditionalReturn(InsertStatement):
    @classmethod
    def should_insert_at_location(cls,
                                  problem: Problem,
                                  location: FileLocation
                                  ) -> bool:
        if not super().should_insert_at_location:
            return False
        if not problem.analysis:
            return True
        return problem.analysis.is_inside_void_function(location)

    @classmethod
    def viable_snippets(cls,
                        problem: Problem,
                        snippets: SnippetDatabase,
                        point: InsertionPoint
                        ) -> Iterator[Snippet]:
        for snippet in super().viable_snippets(problem, snippets, point):
            if snippet.kind == 'guarded-return':
                yield snippet


class InsertConditionalBreak(InsertStatement):
    @classmethod
    def should_insert_at_location(cls,
                                  problem: Problem,
                                  location: FileLocation
                                  ) -> bool:
        if not super().should_insert_at_location:
            return False
        if not problem.analysis:
            return True
        return problem.analysis.is_inside_loop(location)

    @classmethod
    def viable_snippets(cls,
                        problem: Problem,
                        snippets: SnippetDatabase,
                        point: InsertionPoint
                        ) -> Iterator[Snippet]:
        for snippet in super().viable_snippets(problem, snippets, point):
            if snippet.kind == 'guarded-break':
                yield snippet


class ApplyTransformation(RooibosTransformation):
    match = "= :[1];"
    rewrite = "= :[2](:[1]);"

    @classmethod
    def is_valid_match(self, match: rooibos.Match) -> bool:
        return ';' not in match.environment['1'].fragment

    @classmethod
    def match_to_transformations(cls,
                                 problem: Problem,
                                 snippets: SnippetDatabase,
                                 location: FileLocationRange,
                                 environment: rooibos.Environment
                                 ) -> List[Transformation]:
        transformations = []  # type: List[Transformation]

        # TODO find applicable transformations
        for snippet in snippets.in_file(location.filename):
            if snippet.kind != 'transformer':
                continue

            args = {'1': environment['1'].fragment,
                    '2': snippet.content}  # type: Dict[str, str]
            transformation = cls(location, args)
            transformations.append(transformation)

        return transformations


class SignedToUnsigned(RooibosTransformation):
    match = "int :[1] ="
    rewrite = "unsigned int :[1] ="
    constraints = [
        ("1", is_single_token)
    ]

    @classmethod
    def is_valid_match(self, match: rooibos.Match) -> bool:
        return is_single_token(match.environment['1'].fragment)

    # FIXME borko?
    @classmethod
    def match_to_transformations(cls,
                                 problem: Problem,
                                 snippets: SnippetDatabase,
                                 location: FileLocationRange,
                                 environment: rooibos.Environment
                                 ) -> List[Transformation]:
        args = {'1': environment['1'].fragment}  # type: Dict[str, str]
        return [cls(location, args)]  # type: ignore


class AndToOr(RooibosTransformation):
    match = "&&"
    rewrite = "||"


class OrToAnd(RooibosTransformation):
    match = "||"
    rewrite = "&&"


class LEToGT(RooibosTransformation):
    match = "<="
    rewrite = ">"


class GTToLE(RooibosTransformation):
    match = ">"
    rewrite = "<="


class LTToGE(RooibosTransformation):
    match = "<"
    rewrite = ">="


class GEToLT(RooibosTransformation):
    match = ">="
    rewrite = "<"


class EQToNEQ(RooibosTransformation):
    match = "=="
    rewrite = "!="


class NEQToEQ(RooibosTransformation):
    match = "!="
    rewrite = "=="


class PlusToMinus(RooibosTransformation):
    match = "+"
    rewrite = "-"


class MinusToPlus(RooibosTransformation):
    match = "-"
    rewrite = "+"


class DivToMul(RooibosTransformation):
    match = "/"
    rewrite = "*"


class MulToDiv(RooibosTransformation):
    match = "*"
    rewrite = "/"


@attr.s(frozen=True)
class LocationRangeTransformation(Transformation):
    location = attr.ib(type=FileLocationRange,
                       validator=attr.validators.instance_of(FileLocationRange))  # noqa: pycodestyle


@attr.s(frozen=True)
class DeleteTransformation(LocationRangeTransformation):
    def __str__(self) -> str:
        return "DELETE[{}]".format(self.location)

    def to_replacement(self, problem: Problem) -> Replacement:
        return Replacement(self.location, "")


@attr.s(frozen=True)
class ReplaceTransformation(LocationRangeTransformation):
    """
    Replaces a numbered line in a given file with a provided snippet.
    """
    snippet = attr.ib(type=Snippet)

    def __str__(self) -> str:
        return "REPLACE[{}; {}]".format(self.location, self.snippet)

    def to_replacement(self, problem: Problem) -> Replacement:
        return Replacement(self.location, self.snippet.content)


@attr.s(frozen=True)
class AppendTransformation(LocationRangeTransformation):
    """
    Appends a given snippet to a specific line in a given file.
    """
    snippet = attr.ib(type=Snippet)

    def __str__(self) -> str:
        return "APPEND[{}; {}]".format(self.location, self.snippet)

    def to_replacement(self, problem: Problem) -> Replacement:
        old = problem.sources.read_chars(self.location)
        new = old + self.snippet.content
        return Replacement(self.location, new)
