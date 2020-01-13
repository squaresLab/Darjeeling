# -*- coding: utf-8 -*-
__all__ = ('ReplaceStatement',)

from typing import (List, Iterator, Iterable, Dict, Any, FrozenSet, Mapping,
                    Optional, ClassVar)
import logging
import typing

import attr
import kaskara

from .base import StatementTransformation, StatementTransformationSchema
from ..base import Transformation, TransformationSchema
from ..config import TransformationSchemaConfig
from ...snippet import (StatementSnippet, SnippetDatabase,
                        StatementSnippetDatabase)
from ...core import (Replacement, FileLine, FileLocationRange, FileLocation,
                     FileLineSet, Location, LocationRange)

if typing.TYPE_CHECKING:
    from ..problem import Problem

logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@attr.s(frozen=True, repr=False, auto_attribs=True)
class ReplaceStatement(StatementTransformation):
    location: FileLocationRange
    replacement: StatementSnippet

    def __repr__(self) -> str:
        s = "ReplaceStatement[{}]<{}>"
        s = s.format(repr(self.replacement.content), str(self.location))
        return s

    def to_replacement(self, problem: 'Problem') -> Replacement:
        return Replacement(self.location, str(self.replacement.content))

    @property
    def line(self) -> FileLine:
        return FileLine(self.location.filename,
                        self.location.start.line)

    class Schema(StatementTransformationSchema):
        def all_at_statement(self,
                             statement: kaskara.Statement
                             ) -> Iterator[Transformation]:
            problem = self._problem
            snippets = self._snippets

            # do not replace declaration statements
            if problem.settings.ignore_decls and statement.kind == 'DeclStmt':
                return

            check_equiv = problem.settings.ignore_string_equivalent_snippets
            for snippet in self.viable_snippets(statement):
                logger.debug("using snippet: %s", snippet.content)
                eq_content = \
                    not check_equiv and snippet.content == statement.content
                eq_canonical = \
                    check_equiv and snippet.content == statement.canonical
                if eq_content or eq_canonical:
                    logger.debug("prevented self-replacement of statement [%s]",
                                 statement.location)
                else:
                    logger.debug("replace with snippet: %s", snippet.content)
                    yield ReplaceStatement(statement.location, snippet)

    class SchemaConfig(TransformationSchemaConfig):
        NAME: ClassVar[str] = 'replace-statement'

        @classmethod
        def from_dict(cls,
                      d: Mapping[str, Any],
                      dir_: Optional[str] = None
                      ) -> 'TransformationSchemaConfig':
            return ReplaceStatement.SchemaConfig()

        def build(self,
                  problem: 'Problem',
                  snippets: SnippetDatabase
                  ) -> 'TransformationSchema':
            assert isinstance(snippets, StatementSnippetDatabase)
            return ReplaceStatement.Schema(problem=problem, snippets=snippets)
