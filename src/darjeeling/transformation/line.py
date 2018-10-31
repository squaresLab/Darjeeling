"""
This module implements GenProg-style operators for individual source code
lines.
"""
__all__ = [
    'InsertLine',
    'DeleteLine',
    'ReplaceLine'
]

from typing import List, Iterator, Iterable, Dict, Any, FrozenSet
import logging

import attr

from .base import Transformation, register
from ..problem import Problem
from ..snippet import Snippet, SnippetDatabase
from ..core import Replacement, FileLine, FileLocationRange, FileLocation, \
                   FileLineSet, Location, LocationRange

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)


class LineTransformation(Transformation):
    """
    Base class for all line-based transformations.
    """
    @classmethod
    def all_at_lines(cls,
                     problem: Problem,
                     snippets: SnippetDatabase,
                     lines: List[FileLine],
                     *,
                     threads: int = 1
                     ) -> Dict[FileLine, Iterator[Transformation]]:
        return {l: cls.all_at_line(problem, snippets, l) for l in lines}

    @classmethod
    def all_at_line(cls,
                    problem: Problem,
                    snippets: SnippetDatabase,
                    line: FileLine
                    ) -> Iterator[Transformation]:
        raise NotImplementedError

    @classmethod
    def viable_insertions(cls,
                          problem: Problem,
                          context: FileLine
                          ) -> Iterator[FileLine]:
        sources = problem.sources
        filename = context.filename
        for line_num in range(1, sources.num_lines(filename) + 1):
            insertion = FileLine(filename, line_num)
            content = sources.read_line(insertion)
            if content.isspace():
                continue
            yield insertion


@register("delete-line")
@attr.s(frozen=True)
class DeleteLine(LineTransformation):
    line = attr.ib(type=FileLine)

    @classmethod
    def all_at_line(cls, problem, snippets, line):
        yield DeleteLine(line)

    def to_replacement(self, problem: Problem) -> Replacement:
        loc = problem.sources.line_to_location_range(self.line)
        return Replacement(loc, '')


@register("replace-line")
@attr.s(frozen=True)
class ReplaceLine(LineTransformation):
    line = attr.ib(type=FileLine)
    replacement = attr.ib(type=FileLine)

    @classmethod
    def all_at_line(cls, problem, snippets, line):
        for replacement in cls.viable_insertions(problem, line):
            if replacement != line:
                yield ReplaceLine(line, replacement)

    def to_replacement(self, problem: Problem) -> Replacement:
        sources = problem.sources
        loc = sources.line_to_location_range(self.line)
        rep = sources.read_line(self.replacement, keep_newline=True)
        return Replacement(loc, rep)


@register("insert-line")
@attr.s(frozen=True)
class InsertLine(LineTransformation):
    line = attr.ib(type=FileLine)
    insertion = attr.ib(type=FileLine)

    @classmethod
    def all_at_line(cls, problem, snippets, line):
        # TODO append after the last line!
        for ins in cls.viable_insertions(problem, line):
            yield InsertLine(line, ins)

    def to_replacement(self, problem: Problem) -> Replacement:
        sources = problem.sources
        r = sources.line_to_location_range(self.line)
        r = FileLocationRange(r.filename, LocationRange(r.start, r.start))
        ins = sources.read_line(self.insertion, keep_newline=True)
        return Replacement(r, ins)
