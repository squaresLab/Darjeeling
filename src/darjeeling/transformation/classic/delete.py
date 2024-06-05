from __future__ import annotations

__all__ = ("DeleteStatement",)

import typing
from collections.abc import Iterator, Mapping
from typing import Any, ClassVar

import attr

from darjeeling.core import FileLine, FileLocationRange, Replacement
from darjeeling.snippet import SnippetDatabase, StatementSnippetDatabase
from darjeeling.transformation.base import Transformation, TransformationSchema
from darjeeling.transformation.classic.base import StatementTransformation, StatementTransformationSchema
from darjeeling.transformation.config import TransformationSchemaConfig

if typing.TYPE_CHECKING:
    import kaskara

    from darjeeling.problem import Problem


@attr.s(frozen=True, repr=False, auto_attribs=True)
class DeleteStatement(StatementTransformation):
    _schema: StatementTransformationSchema
    statement: kaskara.Statement

    def __repr__(self) -> str:
        return f"DeleteStatement<{self.location!s}>"

    def to_replacement(self) -> Replacement:
        return Replacement(self.location, "")

    @property
    def location(self) -> FileLocationRange:
        return self.statement.location

    @property
    def line(self) -> FileLine:
        return FileLine(self.location.filename, self.location.start.line)

    @property
    def schema(self) -> TransformationSchema:  # type: ignore[type-arg]
        return self._schema


class DeleteStatementSchema(StatementTransformationSchema):
    def find_all_at_statement(
        self,
        statement: kaskara.Statement,
    ) -> Iterator[Transformation]:
        problem = self._problem
        if problem.settings.ignore_decls and statement.kind == "DeclStmt":
            return
        yield DeleteStatement(self, statement)


class DeleteStatementSchemaConfig(TransformationSchemaConfig):
    NAME: ClassVar[str] = "delete-statement"

    @classmethod
    def from_dict(
        cls,
        d: Mapping[str, Any],
        dir_: str | None = None,
    ) -> TransformationSchemaConfig:
        return DeleteStatementSchemaConfig()

    def build(
        self,
        problem: Problem,
        snippets: SnippetDatabase,  # type: ignore[type-arg]
    ) -> TransformationSchema:  # type: ignore[type-arg]
        assert isinstance(snippets, StatementSnippetDatabase)
        return DeleteStatementSchema(problem=problem, snippets=snippets)
