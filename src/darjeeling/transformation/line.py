"""Implements GenProg-style operators for individual source code lines."""
from __future__ import annotations

__all__ = (
    "DeleteLine",
    "InsertLine",
    "ReplaceLine",
)

import abc
import typing as t

import attr
from overrides import overrides

from darjeeling.core import FileLine, FileLocationRange, LocationRange, Replacement
from darjeeling.snippet import LineSnippetDatabase, SnippetDatabase
from darjeeling.transformation.base import Transformation, TransformationSchema
from darjeeling.transformation.config import TransformationSchemaConfig

if t.TYPE_CHECKING:
    from collections.abc import Collection, Iterator, Mapping

    from darjeeling.problem import Problem


class LineTransformation(Transformation):
    """Base class for all line-based transformations."""


@attr.s(frozen=True, auto_attribs=True)
class LineTransformationSchema(TransformationSchema[LineTransformation]):
    _problem: Problem = attr.ib(hash=False)
    _snippets: LineSnippetDatabase = attr.ib(hash=False)

    def find_all_in_file(self, filename: str) -> Iterator[Transformation]:
        m = "find_all_in_file is not required or supported by this schema"
        raise NotImplementedError(m)

    def find_all_at_lines_in_file(
        self,
        filename: str,
        lines: Collection[int],
    ) -> Iterator[Transformation]:
        for line_number in lines:
            file_line = FileLine(filename, line_number)
            yield from self.find_all_at_line(file_line)

    @abc.abstractmethod
    def find_all_at_line(self, line: FileLine) -> Iterator[Transformation]:
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
    _schema: LineTransformationSchema
    line: FileLine

    def to_replacement(self) -> Replacement:
        sources = self._schema._problem.sources
        loc = sources.line_to_location_range(self.line)
        return Replacement(loc, "")

    @property
    def schema(self) -> TransformationSchema:  # type: ignore[type-arg]
        return self._schema

    class Schema(LineTransformationSchema):
        def find_all_at_line(self, line: FileLine) -> Iterator[Transformation]:
            yield DeleteLine(self, line)

    class SchemaConfig(TransformationSchemaConfig):
        NAME = "delete-line"

        @classmethod
        @overrides
        def from_dict(
            cls,
            d: Mapping[str, t.Any],
            dir_: str | None = None,
        ) -> TransformationSchemaConfig:
            return DeleteLine.SchemaConfig()

        def build(
            self,
            problem: Problem,
            snippets: SnippetDatabase,  # type: ignore[type-arg]
        ) -> TransformationSchema:  # type: ignore[type-arg]
            assert isinstance(snippets, LineSnippetDatabase)
            return DeleteLine.Schema(problem=problem, snippets=snippets)


@attr.s(frozen=True, auto_attribs=True)
class ReplaceLine(LineTransformation):
    _schema: LineTransformationSchema
    line: FileLine
    replacement: FileLine

    @property
    def schema(self) -> TransformationSchema:  # type: ignore[type-arg]
        return self._schema

    def to_replacement(self) -> Replacement:
        sources = self._schema._problem.sources
        loc = sources.line_to_location_range(self.line)
        rep = sources.read_line(self.replacement, keep_newline=True)
        return Replacement(loc, rep)

    @attr.s(frozen=True, auto_attribs=True)
    class Schema(LineTransformationSchema):
        def find_all_at_line(self, line: FileLine) -> Iterator[Transformation]:
            for replacement in self.viable_insertions(line):
                if replacement != line:
                    yield ReplaceLine(self, line, replacement)

    class SchemaConfig(TransformationSchemaConfig):
        NAME = "replace-line"

        @classmethod
        def from_dict(
            cls,
            d: Mapping[str, t.Any],
            dir_: str | None = None,
        ) -> TransformationSchemaConfig:
            return ReplaceLine.SchemaConfig()

        def build(
            self,
            problem: Problem,
            snippets: SnippetDatabase,  # type: ignore[type-arg]
        ) -> TransformationSchema:  # type: ignore[type-arg]
            assert isinstance(snippets, LineSnippetDatabase)
            return ReplaceLine.Schema(problem=problem, snippets=snippets)


@attr.s(frozen=True, auto_attribs=True)
class InsertLine(LineTransformation):
    _schema: LineTransformationSchema
    line: FileLine
    insertion: FileLine

    @property
    def schema(self) -> TransformationSchema:  # type: ignore[type-arg]
        return self._schema

    def to_replacement(self) -> Replacement:
        sources = self._schema._problem.sources
        r = sources.line_to_location_range(self.line)
        r = FileLocationRange(r.filename, LocationRange(r.start, r.start))
        ins = sources.read_line(self.insertion, keep_newline=True)
        return Replacement(r, ins)

    class Schema(LineTransformationSchema):
        def find_all_at_line(self, line: FileLine) -> Iterator[Transformation]:
            # TODO append after the last line!
            for ins in self.viable_insertions(line):
                yield InsertLine(self, line, ins)

    class SchemaConfig(TransformationSchemaConfig):
        NAME = "insert-line"

        @classmethod
        @overrides
        def from_dict(
            cls,
            d: Mapping[str, t.Any],
            dir_: str | None = None,
        ) -> TransformationSchemaConfig:
            return InsertLine.SchemaConfig()

        def build(
            self,
            problem: Problem,
            snippets: SnippetDatabase,  # type: ignore[type-arg]
        ) -> TransformationSchema:  # type: ignore[type-arg]
            assert isinstance(snippets, LineSnippetDatabase)
            return InsertLine.Schema(problem=problem, snippets=snippets)
