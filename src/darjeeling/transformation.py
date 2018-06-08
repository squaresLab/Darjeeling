"""
This module is responsible for describing concrete transformations to source
code files.
"""
from typing import List, Iterator, Dict, FrozenSet, Tuple

import attr
import rooibos
from bugzoo.core.bug import Bug

from .problem import Problem
from .snippet import Snippet
from .core import Replacement, FileLine, FileLocationRange


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
        return type.__new__(metacls, name, bases, dikt)


@attr.s(frozen=True)
class RooibosTransformation(Transformation, metaclass=RooibosTransformationMeta):  # noqa: pycodestyle
    location = attr.ib(type=FileLocationRange)
    arguments = attr.ib(type=FrozenSet[Tuple[str, str]],  # TODO replace with FrozenDict
                        converter=frozenset)  # type: ignore

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


class AndToOr(RooibosTransformation):
    match = "&&"
    rewrite = "||"


class OrToAnd(RooibosTransformation):
    match = "||"
    rewrite = "&&"


class GreaterThanToLessOrEqualTo(RooibosTransformation):
    match = ">"
    rewrite = "<="


class LEToGT(RooibosTransformation):
    match = "<="
    rewrite = ">"


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
