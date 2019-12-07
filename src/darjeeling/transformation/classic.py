# -*- coding: utf-8 -*-
"""
This module provides transformation schemas for each of the classical
GenProg-style statement operators.
"""
__all__ = (
    'PrependStatement',
    'DeleteStatement',
    'ReplaceStatement'
)

from typing import List, Iterator, Iterable, Dict, Any, FrozenSet
import abc
import logging

import attr
import kaskara

from .base import Transformation, TransformationSchema, register
from ..problem import Problem
from ..snippet import Snippet, SnippetDatabase
from ..core import Replacement, FileLine, FileLocationRange, FileLocation, \
                   FileLineSet, Location, LocationRange

logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class StatementTransformation(Transformation):
    """Base class for all transformations that are applied to a statement."""


class StatementTransformationSchema(TransformationSchema[StatementTransformation]):  # noqa: pycodestyle
    def all_at_lines(self,
                     problem: Problem,
                     snippets: SnippetDatabase,
                     lines: List[FileLine],
                     *,
                     threads: int = 1
                     ) -> Dict[FileLine, Iterator[Transformation]]:
        return {line: self.all_at_line(problem, snippets, line)
                for line in lines}

    def all_at_line(self,
                    problem: Problem,
                    snippets: SnippetDatabase,
                    line: FileLine
                    ) -> Iterator[Transformation]:
        """
        Returns an iterator over all of the possible transformations of this
        kind that can be performed at a given line.
        """
        analysis = problem.analysis
        if analysis is None:
            logger.warning("cannot determine statement transformations: no Kaskara analysis found")  # noqa: pycodestyle
            return
        statements = analysis.statements.at_line(line)  # type: Iterator[kaskara.Statement]  # noqa: pycodestyle
        for statement in statements:
            yield from self.all_at_statement(problem, snippets, statement)

    @abc.abstractmethod
    def all_at_statement(self,
                         problem: Problem,
                         snippets: SnippetDatabase,
                         statement: kaskara.Statement
                         ) -> Iterator[Transformation]:
        """
        Returns an iterator over all of the possible transformations of this
        kind that can be performed at a given statement.
        """
        ...

    def viable_snippets(self,
                        problem: Problem,
                        snippets: SnippetDatabase,
                        statement: kaskara.Statement
                        ) -> Iterator[Snippet]:
        """
        Returns an iterator over the set of snippets that can be inserted
        immediately before a given statement.
        """
        filename = statement.location.filename
        location = FileLocation(filename, statement.location.start)
        viable = snippets.in_file(filename)

        if problem.settings.only_insert_executed_code:
            executed = problem.coverage.locations
            viable = filter(lambda s: any(l in executed for l in s.lines),
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
            viable = filter(lambda s: in_switch or in_loop or not s.requires_break,  # noqa: pycodestyle
                            viable)

        if problem.settings.use_scope_checking:
            in_scope = statement.visible  # type: FrozenSet[str]
            viable = filter(lambda s: all(v in in_scope for v in s.uses), viable)

        # do not insert code that (only) writes to a dead variable
        if problem.settings.ignore_dead_code:
            live_vars = statement.live_before  # type: FrozenSet[str]
            viable = filter(
                lambda s: not any(w not in live_vars for w in s.writes),
                viable)

        yield from sorted(viable)


@attr.s(frozen=True, repr=False, auto_attribs=True)
class DeleteStatement(StatementTransformation):
    location: FileLocationRange

    def __repr__(self) -> str:
        s = "DeleteStatement<{}>".format(str(self.location))
        return s

    def to_replacement(self, problem: Problem) -> Replacement:
        return Replacement(self.location, '')

    @property
    def line(self) -> FileLine:
        return FileLine(self.location.filename,
                        self.location.start.line)

    @register("delete-statement")
    class Schema(StatementTransformationSchema):
        NAME = 'delete-statement'

        def all_at_statement(self,
                             problem: Problem,
                             snippets: SnippetDatabase,
                             statement: kaskara.Statement
                             ) -> Iterator[Transformation]:
            if problem.settings.ignore_decls and statement.kind == 'DeclStmt':
                return
            yield DeleteStatement(statement.location)


@attr.s(frozen=True, repr=False, auto_attribs=True)
class ReplaceStatement(StatementTransformation):
    location: FileLocationRange
    replacement: Snippet

    def __repr__(self) -> str:
        s = "ReplaceStatement[{}]<{}>"
        s = s.format(repr(self.replacement.content), str(self.location))
        return s

    def to_replacement(self, problem: Problem) -> Replacement:
        return Replacement(self.location, str(self.replacement.content))

    @property
    def line(self) -> FileLine:
        return FileLine(self.location.filename,
                        self.location.start.line)

    @register("replace-statement")
    class Schema(StatementTransformationSchema):
        NAME = 'replace-statement'

        def all_at_statement(self,
                             problem: Problem,
                             snippets: SnippetDatabase,
                             statement: kaskara.Statement
                             ) -> Iterator[Transformation]:
            # do not replace declaration statements
            if problem.settings.ignore_decls and statement.kind == 'DeclStmt':
                return

            check_equiv = problem.settings.ignore_string_equivalent_snippets
            for snippet in self.viable_snippets(problem, snippets, statement):
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


@attr.s(frozen=True, repr=False, auto_attribs=True)
class PrependStatement(StatementTransformation):
    location: FileLocation
    statement: Snippet

    def __repr__(self) -> str:
        s = "PrependStatement[{}]<{}>"
        s = s.format(str(self.location), repr(str(self.statement.content)))
        return s

    @property
    def line(self) -> FileLine:
        return FileLine(self.location.filename,
                        self.location.line)

    def to_replacement(self, problem: Problem) -> Replacement:
        r = FileLocationRange(self.location.filename,
                              LocationRange(self.location.location, self.location.location))
        return Replacement(r, self.statement.content)

    @register("prepend-statement")
    class Schema(StatementTransformationSchema):
        NAME = 'prepend-statement'

        def should_insert_at_location(self,
                                      problem: Problem,
                                      location: FileLocation
                                      ) -> bool:
            """Determines whether an insertion should be made at a location."""
            if not problem.analysis:
                return True
            if not problem.analysis.is_inside_function(location):
                return False
            return True

        def all_at_statement(self,
                             problem: Problem,
                             snippets: SnippetDatabase,
                             statement: kaskara.Statement
                             ) -> Iterator[Transformation]:
            location = FileLocation(statement.location.filename,
                                    statement.location.start)
            if not self.should_insert_at_location(problem, location):
                yield from []
            for snippet in self.viable_snippets(problem, snippets, statement):
                yield PrependStatement(location, snippet)
