"""
This module is responsible for describing concrete transformations to source
code files.
"""
from typing import List, Iterator, Dict, FrozenSet, Tuple
import re
import logging

import attr
import rooibos
from bugzoo.core.bug import Bug

from .problem import Problem
from .snippet import Snippet
from .core import Replacement, FileLine, FileLocationRange

logger = logging.getLogger(__name__)

REGEX_HOLE = re.compile('(?<=:\[)\w+(?=\])')


def is_single_token(snippet: str) -> bool:
    return ' ' not in snippet


class Transformation(object):
    """
    Represents a transformation to a source code file.
    """
    def to_replacement(self, problem: Problem) -> Replacement:
        raise NotImplementedError


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


@attr.s(frozen=True)
class RooibosTransformation(Transformation, metaclass=RooibosTransformationMeta):  # noqa: pycodestyle
    location = attr.ib(type=FileLocationRange)
    arguments = attr.ib(type=FrozenSet[Tuple[str, str]],  # TODO replace with FrozenDict
                        converter=lambda args: frozenset(args.items()))  # type: ignore  # noqa: pycodestyle

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
    @classmethod
    def match_to_transformations(cls,
                                 problem: Problem,
                                 location: FileLocationRange,
                                 environment: rooibos.Environment
                                 ) -> List[Transformation]:
        args = {}  # type: Dict[str, str]
        return [cls(location, args)]  # type: ignore


class InsertVoidFunctionCall(RooibosTransformation):
    match = ";\n"
    rewrite = ";\n:[1]();\n"

    @classmethod
    def is_valid_match(cls, match: rooibos.Match) -> bool:
        # TODO must be inside a function
        return True

    @classmethod
    def match_to_transformations(cls,
                                 problem: Problem,
                                 location: FileLocationRange,
                                 environment: rooibos.Environment
                                 ) -> List[Transformation]:
        # don't insert into small functions

        # don't insert macros?

        # don't insert after a return statement (or a break?)
        line_previous = FileLine(location.filename, location.start.line)
        line_previous_content = \
            problem.sources.read_line(line_previous)
        if ' return ' in line_previous_content:
            return []

        # TODO find all unique insertion points

        # TODO find appropriate void functions
        args = {'1': 'foo'}
        return [cls(location, args)]


class InsertConditionalReturn(RooibosTransformation):
    match = ";\n"
    rewrite = ";\nif(:[1]){return;}\n"

    @classmethod
    def is_valid_match(cls, match: rooibos.Match) -> bool:
        # TODO must be inside a void function
        return True

    @classmethod
    def match_to_transformations(cls,
                                 problem: Problem,
                                 location: FileLocationRange,
                                 environment: rooibos.Environment
                                 ) -> List[Transformation]:
        # TODO contains_return
        # don't insert after a return statement (or a break?)
        line_previous = FileLine(location.filename, location.start.line)
        line_previous_content = \
            problem.sources.read_line(line_previous)
        if ' return ' in line_previous_content:
            return []

        # TODO find all unique insertion points

        # TODO find appropriate if guards
        args = {'1': 'true'}
        return [cls(location, args)]


class InsertConditionalBreak(RooibosTransformation):
    match = ";\n"
    rewrite = ";\nif(:[1]){break;}\n"

    @classmethod
    def is_valid_match(cls, match: rooibos.Match) -> bool:
        # TODO must be inside a loop
        return True

    @classmethod
    def match_to_transformations(cls,
                                 problem: Problem,
                                 location: FileLocationRange,
                                 environment: rooibos.Environment
                                 ) -> List[Transformation]:
        # TODO contains_return
        # don't insert after a return statement (or a break?)
        line_previous = FileLine(location.filename, location.start.line)
        line_previous_content = \
            problem.sources.read_line(line_previous)
        if ' return ' in line_previous_content:
            return []

        # TODO find all unique insertion points

        # TODO find appropriate if guards
        args = {'1': 'true'}
        return [cls(location, args)]


class ApplyTransformation(RooibosTransformation):
    match = "= :[1];"
    rewrite = "= :[2](:[1]);"

    @classmethod
    def is_valid_match(self, match: rooibos.Match) -> bool:
        return ';' not in match.environment['1'].fragment

    @classmethod
    def match_to_transformations(cls,
                                 problem: Problem,
                                 location: FileLocationRange,
                                 environment: rooibos.Environment
                                 ) -> List[Transformation]:
        # TODO find applicable transformations
        args = {'1': environment['1'].fragment,
                '2': 'foo'}  # type: Dict[str, str]
        return [cls(location, args)]  # type: ignore


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
