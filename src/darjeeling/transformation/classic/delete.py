# -*- coding: utf-8 -*-
__all__ = ('DeleteStatement',)

from typing import Any, ClassVar, Iterator, Mapping, Optional
import typing

import attr
import kaskara

from .base import StatementTransformation, StatementTransformationSchema
from ..base import Transformation, TransformationSchema
from ..config import TransformationSchemaConfig
from ...snippet import SnippetDatabase, StatementSnippetDatabase
from ...core import Replacement, FileLine, FileLocationRange

if typing.TYPE_CHECKING:
    from ..problem import Problem


@attr.s(frozen=True, repr=False, auto_attribs=True)
class DeleteStatement(StatementTransformation):
    _schema: StatementTransformationSchema
    statement: kaskara.Statement

    def __repr__(self) -> str:
        return f"DeleteStatement<{str(self.location)}>"

    def to_replacement(self) -> Replacement:
        return Replacement(self.location, '')

    @property
    def location(self) -> FileLocationRange:
        return self.statement.location

    @property
    def line(self) -> FileLine:
        return FileLine(self.location.filename, self.location.start.line)

    @property
    def schema(self) -> TransformationSchema:
        return self._schema


class DeleteStatementSchema(StatementTransformationSchema):
    def find_all_at_statement(self,
                              statement: kaskara.Statement
                              ) -> Iterator[Transformation]:
        problem = self._problem
        if problem.settings.ignore_decls and statement.kind == 'DeclStmt':
            return
        yield DeleteStatement(self, statement)


class DeleteStatementSchemaConfig(TransformationSchemaConfig):
    NAME: ClassVar[str] = 'delete-statement'

    @classmethod
    def from_dict(cls,
                  d: Mapping[str, Any],
                  dir_: Optional[str] = None
                  ) -> 'TransformationSchemaConfig':
        return DeleteStatementSchemaConfig()

    def build(self,
              problem: 'Problem',
              snippets: SnippetDatabase
              ) -> 'TransformationSchema':
        assert isinstance(snippets, StatementSnippetDatabase)
        return DeleteStatementSchema(problem=problem, snippets=snippets)
