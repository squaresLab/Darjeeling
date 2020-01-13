# -*- coding: utf-8 -*-
"""
This module implements GenProg-style operators for individual source code
lines.
"""
__all__ = ('InsertLine', 'DeleteLine', 'ReplaceLine')

from typing import (List, Iterator, Iterable, Dict, Any, FrozenSet, Mapping,
                    Optional)
import abc
import typing

import attr

from .base import Transformation, TransformationSchema
from .config import TransformationSchemaConfig
from ..snippet import Snippet, SnippetDatabase, LineSnippetDatabase
from ..core import (Replacement, FileLine, FileLocationRange, FileLocation,
                    FileLineSet, Location, LocationRange)
from ..exceptions import BadConfigurationException

if typing.TYPE_CHECKING:
    from ..problem import Problem


class LineTransformation(Transformation):
    """Base class for all line-based transformations."""


@attr.s(frozen=True, auto_attribs=True)
class LineTransformationSchema(TransformationSchema[LineTransformation]):
    _problem: 'Problem' = attr.ib(hash=False)
    _snippets: LineSnippetDatabase = attr.ib(hash=False)

    @classmethod
    def build(cls,
              problem: 'Problem',
              snippets: SnippetDatabase,
              threads: int
              ) -> 'TransformationSchema':
        if not isinstance(snippets, LineSnippetDatabase):
            m = 'line transformations require a line snippet pool'
            raise BadConfigurationException(m)
        return cls(problem=problem, snippets=snippets)

    def all_at_lines(self,
                     lines: List[FileLine]
                     ) -> Mapping[FileLine, Iterator[Transformation]]:
        return {l: self.all_at_line(l) for l in lines}

    @abc.abstractmethod
    def all_at_line(self, line: FileLine) -> Iterator[Transformation]:
        ...

    def viable_insertions(self, context: FileLine) -> Iterator[FileLine]:
        sources = self._problem.sources
        filename = context.filename
        for line_num in range(1, sources.num_lines(filename) + 1):
            insertion = FileLine(filename, line_num)
            content = sources.read_line(insertion)
            if content.isspace():
                continue
            yield insertion


@attr.s(frozen=True, auto_attribs=True)
class DeleteLine(LineTransformation):
    schema: LineTransformationSchema
    line: FileLine

    def to_replacement(self) -> Replacement:
        sources = self.schema._problem.sources
        loc = sources.line_to_location_range(self.line)
        return Replacement(loc, '')

    class Schema(LineTransformationSchema):
        def all_at_line(self, line: FileLine) -> Iterator[Transformation]:
            yield DeleteLine(self, line)

    class SchemaConfig(TransformationSchemaConfig):
        NAME = 'delete-line'

        @classmethod
        def from_dict(cls,
                      d: Mapping[str, Any],
                      dir_: Optional[str] = None
                      ) -> 'TransformationSchemaConfig':
            return DeleteLine.SchemaConfig()

        def build(self,
                  problem: 'Problem',
                  snippets: SnippetDatabase
                  ) -> 'TransformationSchema':
            assert isinstance(snippets, LineSnippetDatabase)
            return DeleteLine.Schema(problem=problem, snippets=snippets)


@attr.s(frozen=True, auto_attribs=True)
class ReplaceLine(LineTransformation):
    schema: LineTransformationSchema
    line: FileLine
    replacement: FileLine

    def to_replacement(self) -> Replacement:
        sources = self.schema._problem.sources
        loc = sources.line_to_location_range(self.line)
        rep = sources.read_line(self.replacement, keep_newline=True)
        return Replacement(loc, rep)

    @attr.s(frozen=True, auto_attribs=True)
    class Schema(LineTransformationSchema):
        def all_at_line(self, line: FileLine) -> Iterator[Transformation]:
            for replacement in self.viable_insertions(line):
                if replacement != line:
                    yield ReplaceLine(self, line, replacement)

    class SchemaConfig(TransformationSchemaConfig):
        NAME = 'replace-line'

        @classmethod
        def from_dict(cls,
                      d: Mapping[str, Any],
                      dir_: Optional[str] = None
                      ) -> 'TransformationSchemaConfig':
            return ReplaceLine.SchemaConfig()

        def build(self,
                  problem: 'Problem',
                  snippets: SnippetDatabase
                  ) -> 'TransformationSchema':
            assert isinstance(snippets, LineSnippetDatabase)
            return ReplaceLine.Schema(problem=problem, snippets=snippets)


@attr.s(frozen=True, auto_attribs=True)
class InsertLine(LineTransformation):
    schema: LineTransformationSchema
    line: FileLine
    insertion: FileLine

    def to_replacement(self) -> Replacement:
        sources = self.schema._problem.sources
        r = sources.line_to_location_range(self.line)
        r = FileLocationRange(r.filename, LocationRange(r.start, r.start))
        ins = sources.read_line(self.insertion, keep_newline=True)
        return Replacement(r, ins)

    class Schema(LineTransformationSchema):
        def all_at_line(self, line: FileLine) -> Iterator[Transformation]:
            # TODO append after the last line!
            for ins in self.viable_insertions(line):
                yield InsertLine(self, line, ins)

    class SchemaConfig(TransformationSchemaConfig):
        NAME = 'insert-line'

        @classmethod
        def from_dict(cls,
                      d: Mapping[str, Any],
                      dir_: Optional[str] = None
                      ) -> 'TransformationSchemaConfig':
            return InsertLine.SchemaConfig()

        def build(self,
                  problem: 'Problem',
                  snippets: SnippetDatabase
                  ) -> 'TransformationSchema':
            assert isinstance(snippets, LineSnippetDatabase)
            return InsertLine.Schema(problem=problem, snippets=snippets)
