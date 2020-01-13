# -*- coding: utf-8 -*-
__all__ = ('PrependStatement',)

from typing import (List, Iterator, Iterable, Dict, Any, FrozenSet, Mapping,
                    Optional, ClassVar)
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


@attr.s(frozen=True, repr=False, auto_attribs=True)
class PrependStatement(StatementTransformation):
    location: FileLocation
    statement: StatementSnippet

    def __repr__(self) -> str:
        s = "PrependStatement[{}]<{}>"
        s = s.format(str(self.location), repr(str(self.statement.content)))
        return s

    @property
    def line(self) -> FileLine:
        return FileLine(self.location.filename,
                        self.location.line)

    def to_replacement(self, problem: 'Problem') -> Replacement:
        r = FileLocationRange(self.location.filename,
                              LocationRange(self.location.location, self.location.location))
        return Replacement(r, self.statement.content)

    class Schema(StatementTransformationSchema):
        def should_insert_at_location(self, location: FileLocation) -> bool:
            """Determines whether an insertion should be made at a location."""
            problem = self._problem
            if not problem.analysis:
                return True
            if not problem.analysis.is_inside_function(location):
                return False
            return True

        def all_at_statement(self,
                             statement: kaskara.Statement
                             ) -> Iterator[Transformation]:
            location = FileLocation(statement.location.filename,
                                    statement.location.start)
            if not self.should_insert_at_location(location):
                yield from []
            for snippet in self.viable_snippets(statement):
                yield PrependStatement(location, snippet)

    class SchemaConfig(TransformationSchemaConfig):
        NAME: ClassVar[str] = 'prepend-statement'

        @classmethod
        def from_dict(cls,
                      d: Mapping[str, Any],
                      dir_: Optional[str] = None
                      ) -> 'TransformationSchemaConfig':
            return PrependStatement.SchemaConfig()

        def build(self,
                  problem: 'Problem',
                  snippets: SnippetDatabase
                  ) -> 'TransformationSchema':
            assert isinstance(snippets, StatementSnippetDatabase)
            return PrependStatement.Schema(problem=problem, snippets=snippets)
