from __future__ import annotations

__all__ = ("ReplaceStatement",)

import typing
from typing import Any, ClassVar

import attr
from loguru import logger

import darjeeling.exceptions as exc
from darjeeling.core import FileLine, FileLocationRange, Replacement
from darjeeling.snippet import SnippetDatabase, StatementSnippet, StatementSnippetDatabase
from darjeeling.transformation.classic.base import StatementTransformation, StatementTransformationSchema
from darjeeling.transformation.config import TransformationSchemaConfig

if typing.TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    import kaskara

    from darjeeling.problem import Problem
    from darjeeling.transformation.base import Transformation, TransformationSchema


@attr.s(frozen=True, repr=False, auto_attribs=True)
class ReplaceStatement(StatementTransformation):
    _schema: ReplaceStatementSchema
    at: kaskara.Statement
    replacement: StatementSnippet

    @property
    def schema(self) -> TransformationSchema:  # type: ignore[type-arg]
        return self._schema

    def __repr__(self) -> str:
        s = "ReplaceStatement[{}]<{}>"
        return s.format(repr(self.replacement.content), str(self.location))

    def to_replacement(self) -> Replacement:
        # TODO toggle via preserve_indentation
        # determine and apply appropriate indentation
        indentation = self._schema._indentation(self.at)
        source = self.replacement.content
        source = self._schema._source_with_indentation(source, indentation)
        return Replacement(self.location, source)

    @property
    def location(self) -> FileLocationRange:
        return self.at.location

    @property
    def line(self) -> FileLine:
        return FileLine(
            self.location.filename,
            self.location.start.line,
        )


class ReplaceStatementSchema(StatementTransformationSchema):
    def find_all_at_statement(
        self,
        statement: kaskara.Statement,
    ) -> Iterator[Transformation]:
        problem = self._problem

        # do not replace declaration statements
        if problem.settings.ignore_decls and statement.kind == "DeclStmt":
            return

        check_equiv = problem.settings.ignore_string_equivalent_snippets
        for snippet in self.viable_snippets(statement):
            logger.debug(f"using snippet: {snippet.content}")
            eq_content = \
                not check_equiv and snippet.content == statement.content
            eq_canonical = \
                check_equiv and snippet.content == statement.canonical
            if eq_content or eq_canonical:
                logger.debug("prevented self-replacement of statement "
                             f"[{statement.location}]")
            else:
                logger.debug(f"replace with snippet: {snippet.content}")
                yield ReplaceStatement(self, statement, snippet)


@attr.s(frozen=True)
class ReplaceStatementSchemaConfig(TransformationSchemaConfig):
    NAME: ClassVar[str] = "replace-statement"

    preserve_indentation: bool = attr.ib()

    @classmethod
    def from_dict(
        cls,
        d: Mapping[str, Any],
        dir_: str | None = None,
    ) -> TransformationSchemaConfig:
        if "preserve_indentation" not in d:
            preserve_indentation = True
        else:
            preserve_indentation = d["preserve-indentation"]
            if not isinstance(preserve_indentation, bool):
                m = "illegal value for 'preserve-indentation': expected bool"
                raise exc.BadConfigurationException(m)

        return ReplaceStatementSchemaConfig(
            preserve_indentation=preserve_indentation)

    def build(
        self,
        problem: Problem,
        snippets: SnippetDatabase,  # type: ignore[type-arg]
    ) -> TransformationSchema:  # type: ignore[type-arg]
        assert isinstance(snippets, StatementSnippetDatabase)
        return ReplaceStatementSchema(problem=problem, snippets=snippets)
