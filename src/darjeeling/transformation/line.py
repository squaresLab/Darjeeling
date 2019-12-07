# -*- coding: utf-8 -*-
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
import abc
import logging

import attr

from .base import Transformation, TransformationSchema, register
from ..problem import Problem
from ..snippet import Snippet, SnippetDatabase
from ..core import Replacement, FileLine, FileLocationRange, FileLocation, \
                   FileLineSet, Location, LocationRange

logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class LineTransformation(Transformation):
    """Base class for all line-based transformations."""


class LineTransformationSchema(TransformationSchema):
    def all_at_lines(self,
                     problem: Problem,
                     snippets: SnippetDatabase,
                     lines: List[FileLine],
                     *,
                     threads: int = 1
                     ) -> Dict[FileLine, Iterator[Transformation]]:
        return {l: self.all_at_line(problem, snippets, l) for l in lines}

    @abc.abstractmethod
    def all_at_line(self,
                    problem: Problem,
                    snippets: SnippetDatabase,
                    line: FileLine
                    ) -> Iterator[Transformation]:
        ...

    def viable_insertions(self,
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


@attr.s(frozen=True, auto_attribs=True)
class DeleteLine(LineTransformation):
    line: FileLine

    def to_replacement(self, problem: Problem) -> Replacement:
        loc = problem.sources.line_to_location_range(self.line)
        return Replacement(loc, '')

    @register('delete-line')
    class Schema(LineTransformationSchema):
        NAME = 'delete-line'

        def all_at_line(self, problem, snippets, line):
            yield DeleteLine(line)


@attr.s(frozen=True, auto_attribs=True)
class ReplaceLine(LineTransformation):
    line: FileLine
    replacement: FileLine

    def to_replacement(self, problem: Problem) -> Replacement:
        sources = problem.sources
        loc = sources.line_to_location_range(self.line)
        rep = sources.read_line(self.replacement, keep_newline=True)
        return Replacement(loc, rep)

    @register('replace-line')
    class Schema(LineTransformationSchema):
        NAME = 'replace-line'

        def all_at_line(self, problem, snippets, line):
            for replacement in cls.viable_insertions(problem, line):
                if replacement != line:
                    yield ReplaceLine(line, replacement)


@attr.s(frozen=True, auto_attribs=True)
class InsertLine(LineTransformation):
    line: FileLine
    insertion: FileLine

    def to_replacement(self, problem: Problem) -> Replacement:
        sources = problem.sources
        r = sources.line_to_location_range(self.line)
        r = FileLocationRange(r.filename, LocationRange(r.start, r.start))
        ins = sources.read_line(self.insertion, keep_newline=True)
        return Replacement(r, ins)

    @register("insert-line")
    class Schema(LineTransformationSchema):
        NAME = 'insert-line'

        def all_at_line(self, problem, snippets, line):
            # TODO append after the last line!
            for ins in self.viable_insertions(problem, line):
                yield InsertLine(line, ins)
