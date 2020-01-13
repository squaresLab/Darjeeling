# -*- coding: utf-8 -*-
__all__ = ('StatementTransformation', 'StatementTransformationSchema')

from typing import Generic, List, Iterator, FrozenSet, Mapping, TypeVar
import abc
import typing

from loguru import logger
import attr
import kaskara

from ..base import Transformation, TransformationSchema
from ..config import TransformationSchemaConfig
from ...snippet import (StatementSnippet, SnippetDatabase,
                        StatementSnippetDatabase)
from ...core import (Replacement, FileLine, FileLocationRange, FileLocation,
                     FileLineSet, Location, LocationRange)
from ...exceptions import BadConfigurationException

if typing.TYPE_CHECKING:
    from ..problem import Problem


class StatementTransformation(Transformation):
    """Base class for all transformations that are applied to a statement."""


@attr.s(frozen=True, auto_attribs=True)
class StatementTransformationSchema(TransformationSchema):
    _problem: 'Problem' = attr.ib(hash=False)
    _snippets: StatementSnippetDatabase = attr.ib(hash=False)

    @classmethod
    def build(cls,
              problem: 'Problem',
              snippets: SnippetDatabase,
              threads: int
              ) -> 'TransformationSchema':
        if not isinstance(snippets, StatementSnippetDatabase):
            m = 'statement transformations require a statement snippet pool'
            raise BadConfigurationException(m)
        return cls(problem=problem, snippets=snippets)

    @staticmethod
    def _source_with_indentation(source: str,
                                 indentation: str,
                                 *,
                                 indent_first_line: bool = False
                                 ) -> str:
        """Applies indentation to a given source."""
        lines = source.split('\n')
        for i in range(0 if indent_first_line else 1, len(lines)):
            if lines[i]:  # don't indent blank lines
                lines[i] = indentation + lines[i]
        return '\n'.join(lines)

    def _indentation(self, statement: kaskara.Statement) -> str:
        """Retrieves the indentation string for a given statement."""
        location = statement.location

        if location.start.column == 0:
            return ''

        line = location.start.line
        start = Location(line, 0)
        stop = Location(line, location.start.column)
        indentation_range = \
            FileLocationRange(location.filename, LocationRange(start, stop))
        indentation = self._problem.sources.read_chars(indentation_range)
        return indentation

    def all_at_lines(self,
                     lines: List[FileLine],
                     ) -> Mapping[FileLine, Iterator[Transformation]]:
        return {line: self.all_at_line(line) for line in lines}

    def all_at_line(self, line: FileLine) -> Iterator[Transformation]:
        """
        Returns an iterator over all of the possible transformations of this
        kind that can be performed at a given line.
        """
        problem = self._problem
        analysis = problem.analysis
        if analysis is None:
            logger.warning("cannot determine statement transformations: "
                           "no Kaskara analysis found")
            return
        statements: Iterator[kaskara.Statement] = analysis.statements.at_line(line)  # noqa
        for statement in statements:
            yield from self.all_at_statement(statement)

    @abc.abstractmethod
    def all_at_statement(self,
                         statement: kaskara.Statement
                         ) -> Iterator[Transformation]:
        """
        Returns an iterator over all of the possible transformations of this
        kind that can be performed at a given statement.
        """
        ...

    def viable_snippets(self,
                        statement: kaskara.Statement
                        ) -> Iterator[StatementSnippet]:
        """
        Returns an iterator over the set of snippets that can be inserted
        immediately before a given statement.
        """
        snippets: StatementSnippetDatabase = self._snippets
        problem = self._problem
        filename = statement.location.filename
        location = FileLocation(filename, statement.location.start)
        viable = snippets.in_file(filename)
        get_lines = snippets.lines_for_snippet

        if problem.settings.only_insert_executed_code:
            executed = problem.coverage.locations
            viable = filter(lambda s: any(l in executed for l in get_lines(s)),
                            viable)

        # do not insert declaration statements
        if problem.settings.ignore_decls:
            assert problem.analysis
            viable = filter(lambda s: s.kind != 'DeclStmt', viable)

        if problem.settings.use_syntax_scope_checking:
            assert problem.analysis
            in_loop = problem.analysis.is_inside_loop(location)
            in_switch = False  # FIXME
            viable = filter(lambda s: in_loop or not s.requires_continue,
                            viable)
            viable = filter(lambda s: in_switch or in_loop or not s.requires_break,  # noqa
                            viable)

        if problem.settings.use_scope_checking:
            in_scope: FrozenSet[str] = statement.visible
            viable = filter(lambda s: all(v in in_scope for v in s.uses), viable)

        # do not insert code that (only) writes to a dead variable
        if problem.settings.ignore_dead_code:
            live_vars: FrozenSet[str] = statement.live_before
            viable = filter(
                lambda s: not any(w not in live_vars for w in s.writes),
                viable)

        yield from sorted(viable)
