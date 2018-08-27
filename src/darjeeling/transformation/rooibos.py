__all__ = [
    'RooibosTransformation',
    'ApplyTransformation',
    'SignedToUnsigned',
    'AndToOr',
    'OrToAnd',
    'LEToGT',
    'GTToLE',
    'LTToGE',
    'GEToLT',
    'EQToNEQ',
    'NEQToEQ',
    'PlusToMinus',
    'MinusToPlus',
    'DivToMul',
    'MulToDiv'
]

from typing import Dict, FrozenSet, Tuple, List, Iterator, Iterable, Optional
from timeit import default_timer as timer
from concurrent.futures import ThreadPoolExecutor
import re
import logging

import attr
import rooibos
import kaskara

from .base import Transformation, register
from ..snippet import Snippet, SnippetDatabase
from ..core import Replacement, FileLine, FileLocationRange, FileLocation, \
                   FileLineSet, Location, LocationRange
from ..problem import Problem

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)

REGEX_HOLE = re.compile('(?<=:\[)\w+(?=\])')


def is_single_token(snippet: str) -> bool:
    return ' ' not in snippet


class RooibosTransformationMeta(type):
    def __new__(metacls: type, name: str, bases, dikt):
        if name != 'RooibosTransformation':
            if not 'match' in dikt:
                raise SyntaxError('missing "match" property in {}'.format(name))
            if not 'rewrite' in dikt:
                raise SyntaxError('missing "rewrite" property in {}'.format(name))
        # TODO add ability to specify constraints

        # determine free holes
        # holes_match = REGEX_HOLE.findall(dikt['match'])  # type: List[str]
        # holes_rewrite = REGEX_HOLE.findall(dikt['rewrite'])  # type: List[str]

        # synthesise a "is_valid_match" function for this transformation

        # TODO compose a fast rewrite function
        return type.__new__(metacls, name, bases, dikt)


@attr.s(frozen=True, repr=False)
class RooibosTransformation(Transformation, metaclass=RooibosTransformationMeta):  # noqa: pycodestyle
    location = attr.ib(type=FileLocationRange)
    arguments = attr.ib(type=FrozenSet[Tuple[str, str]],  # TODO replace with FrozenDict
                        converter=lambda args: frozenset(args.items()))  # type: ignore  # noqa: pycodestyle

    @classmethod
    def matches_in_file(cls,
                        problem: Problem,
                        filename: str
                        ) -> List[rooibos.Match]:
        """
        Returns an iterator over all of the matches of this transformation's
        schema in a given file.
        """
        client_rooibos = problem.rooibos
        file_contents = problem.sources.read_file(filename)
        logger.debug("finding matches of %s in %s", cls.__name__, filename)
        time_start = timer()
        matches = list(client_rooibos.matches(file_contents, cls.match))
        time_taken = timer() - time_start
        logger.debug("found %d matches of %s in %s (took %.3f seconds)",
                     len(matches), cls.__name__, filename, time_taken)
        return matches

    @classmethod
    def all_at_lines(cls,
                     problem: Problem,
                     snippets: SnippetDatabase,
                     lines: List[FileLine],
                     *,
                     threads: int = 1
                     ) -> Dict[FileLine, Iterator[Transformation]]:
        analysis = problem.analysis  # type: Optional[kaskara.Analysis]
        file_to_matches = {}  # type: Dict[str, List[rooibos.Match]]
        filenames = FileLineSet.from_iter(lines).files
        logger.debug("finding all matches of %s in files: %s",
                     cls.__name__, filenames)
        with ThreadPoolExecutor(max_workers=threads) as executor:
            file_to_matches = dict(
                executor.map(lambda f: (f, cls.matches_in_file(problem, f)),
                             filenames))

        num_matches = 0
        line_to_matches = {}  # type: Dict[FileLine, List[rooibos.Match]]
        for (filename, matches_in_file) in file_to_matches.items():
            for match in matches_in_file:
                line = FileLine(filename, match.location.start.line)
                floc = FileLocation(filename,
                                    Location(match.location.start.line,
                                             match.location.start.col))

                # ignore matches at out-of-scope lines
                if line not in lines:
                    continue

                # ignore invalid matches
                if not cls.is_valid_match(match):
                    continue

                # ignore anything outside of a function
                if analysis and not analysis.is_inside_function(floc):
                    continue

                num_matches += 1
                if line not in line_to_matches:
                    line_to_matches[line] = []
                line_to_matches[line].append(match)
        logger.debug("found %d matches of %s across all lines",
                     num_matches, cls.__name__)

        def matches_at_line_to_transformations(line: FileLine,
                                               matches: Iterable[rooibos.Match],
                                               ) -> Iterator[Transformation]:
            """
            Converts a stream of matches at a given line into a stream of
            transformations.
            """
            filename = line.filename
            for match in matches:
                logger.debug("transforming match [%s] to transformations",
                             match)
                loc_start = Location(match.location.start.line,
                                     match.location.start.col)
                loc_stop = Location(match.location.stop.line,
                                     match.location.stop.col)
                location = FileLocationRange(filename,
                                             LocationRange(loc_start, loc_stop))
                yield from cls.match_to_transformations(problem,
                                                        snippets,
                                                        location,
                                                        match.environment)

        line_to_transformations = {
            line: matches_at_line_to_transformations(line, matches_at_line)
            for (line, matches_at_line) in line_to_matches.items()
        }  # type: Dict[FileLine, Iterator[Transformation]]
        return line_to_transformations

    # FIXME need to use abstract properties
    @property
    def rewrite(self) -> str:
        raise NotImplementedError

    @property
    def match(self) -> str:
        raise NotImplementedError

    def to_replacement(self, problem: Problem) -> Replacement:
        args = dict(self.arguments)
        text = problem.rooibos.substitute(self.rewrite, args)
        return Replacement(self.location, text)

    # FIXME implement using constraints
    @classmethod
    def is_valid_match(cls, match: rooibos.Match) -> bool:
        return True

    # FIXME automagically generate
    # FIXME return an Iterable
    @classmethod
    def match_to_transformations(cls,
                                 problem: Problem,
                                 snippets: SnippetDatabase,
                                 location: FileLocationRange,
                                 environment: rooibos.Environment
                                 ) -> List[Transformation]:
        args = {}  # type: Dict[str, str]
        return [cls(location, args)]  # type: ignore

    def __repr__(self) -> str:
        args = ["{}: {}".format(str(k), str(v))
                for (k, v) in dict(self.arguments).items()]
        s_args = "<{}>".format('; '.join(args)) if args else ""
        s = "{}[{}]{}"
        s = s.format(self.__class__.__name__, str(self.location), s_args)
        return s


@register("ApplyTransformation")
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


@register("SignedToUnsigned")
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


@register("AndToOr")
class AndToOr(RooibosTransformation):
    match = "&&"
    rewrite = "||"


@register("OrToAnd")
class OrToAnd(RooibosTransformation):
    match = "||"
    rewrite = "&&"


@register("LEToGT")
class LEToGT(RooibosTransformation):
    match = "<="
    rewrite = ">"


@register("GTToLE")
class GTToLE(RooibosTransformation):
    match = ">"
    rewrite = "<="


@register("LTToGE")
class LTToGE(RooibosTransformation):
    match = "<"
    rewrite = ">="


@register("GEToLT")
class GEToLT(RooibosTransformation):
    match = ">="
    rewrite = "<"


@register("EQToNEQ")
class EQToNEQ(RooibosTransformation):
    match = "=="
    rewrite = "!="


@register("NEQToEQ")
class NEQToEQ(RooibosTransformation):
    match = "!="
    rewrite = "=="


@register("PlusToMinus")
class PlusToMinus(RooibosTransformation):
    match = "+"
    rewrite = "-"


@register("MinusToPlus")
class MinusToPlus(RooibosTransformation):
    match = "-"
    rewrite = "+"


@register("DivToMul")
class DivToMul(RooibosTransformation):
    match = "/"
    rewrite = "*"


@register("MulToDiv")
class MulToDiv(RooibosTransformation):
    match = "*"
    rewrite = "/"
