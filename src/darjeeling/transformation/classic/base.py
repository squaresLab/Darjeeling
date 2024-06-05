from __future__ import annotations

__all__ = ("StatementTransformation", "StatementTransformationSchema")

import abc
import typing as t
from collections.abc import Collection, Iterator

import attr
import kaskara
from loguru import logger

from darjeeling.snippet import StatementSnippet, StatementSnippetDatabase
from darjeeling.transformation.base import Transformation, TransformationSchema

from ...core import (
    FileLine,
    FileLocation,
    FileLocationRange,
    Location,
    LocationRange,
)

if t.TYPE_CHECKING:
    from darjeeling.problem import Problem


class StatementTransformation(Transformation):
    """Base class for all transformations that are applied to a statement."""


@attr.s(frozen=True, auto_attribs=True)
class StatementTransformationSchema(TransformationSchema[StatementTransformation]):
    _problem: Problem = attr.ib(hash=False)
    _snippets: StatementSnippetDatabase = attr.ib(hash=False)

    @staticmethod
    def _source_with_indentation(source: str,
                                 indentation: str,
                                 *,
                                 indent_first_line: bool = False,
                                 ) -> str:
        """Applies indentation to a given source."""
        lines = source.split("\n")
        for i in range(0 if indent_first_line else 1, len(lines)):
            if lines[i]:  # don't indent blank lines
                lines[i] = indentation + lines[i]
        return "\n".join(lines)

    def _indentation(self, statement: kaskara.Statement) -> str:
        """Retrieves the indentation string for a given statement."""
        location = statement.location

        if location.start.column == 0:
            return ""

        line = location.start.line
        start = Location(line, 0)
        stop = Location(line, location.start.column)
        indentation_range = \
            FileLocationRange(location.filename, LocationRange(start, stop))
        indentation = self._problem.sources.read_chars(indentation_range)
        return indentation

    def find_all_in_file(self, filename: str) -> Iterator[Transformation]:
        m = "find_all_in_file is not required or supported by this schema"
        raise NotImplementedError(m)

    def find_all_at_lines_in_file(self,
                                  filename: str,
                                  lines: Collection[int],
                                  ) -> Iterator[Transformation]:
        for line_number in lines:
            file_line = FileLine(filename, line_number)
            yield from self.find_all_at_line(file_line)

    def find_all_at_line(self, line: FileLine) -> Iterator[Transformation]:
        """Returns an iterator over all of the possible transformations of this
        kind that can be performed at a given line.
        """
        problem = self._problem
        analysis = problem.analysis
        if analysis is None:
            logger.warning("cannot determine statement transformations: "
                           "no Kaskara analysis found")
            return
        statements: Iterator[kaskara.Statement] = analysis.statements.at_line(line)
        for statement in statements:
            yield from self.find_all_at_statement(statement)

    @abc.abstractmethod
    def find_all_at_statement(self,
                              statement: kaskara.Statement,
                              ) -> Iterator[Transformation]:
        """Returns an iterator over all of the possible transformations of this
        kind that can be performed at a given statement.
        """
        ...

    def viable_snippets(self,
                        statement: kaskara.Statement,
                        ) -> Iterator[StatementSnippet]:
        """Returns an iterator over the set of snippets that can be inserted
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
            viable = filter(lambda s: any(line in executed for line in get_lines(s)),
                            viable)

        # do not insert declaration statements
        if problem.settings.ignore_decls:
            assert problem.analysis
            viable = filter(lambda s: s.kind != "DeclStmt", viable)

        if problem.settings.use_syntax_scope_checking:
            assert problem.analysis
            in_loop = problem.analysis.is_inside_loop(location)
            in_switch = False  # FIXME
            viable = filter(lambda s: in_loop or not s.requires_continue,
                            viable)
            viable = filter(lambda s: in_switch or in_loop or not s.requires_break,
                            viable)

        if problem.settings.use_scope_checking:
            assert statement.visible is not None
            in_scope: frozenset[str] = statement.visible
            viable = filter(lambda s: all(v in in_scope for v in s.uses), viable)

        # do not insert code that (only) writes to a dead variable
        if problem.settings.ignore_dead_code and hasattr(statement, "live_before"):
            assert statement.live_before is not None
            live_vars: frozenset[str] = statement.live_before
            viable = filter(
                lambda s: not any(w not in live_vars for w in s.writes),
                viable)

        yield from sorted(viable)
