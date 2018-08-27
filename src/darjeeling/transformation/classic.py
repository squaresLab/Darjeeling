__all__ = [
    'InsertStatement',
    'DeleteStatement',
    'ReplaceStatement'
]

from typing import List, Iterator, Iterable, Dict, Any
import logging

import attr
import kaskara

from .base import Transformation, register
from ..problem import Problem
from ..snippet import Snippet, SnippetDatabase
from ..core import Replacement, FileLine, FileLocationRange, FileLocation, \
                   FileLineSet, Location, LocationRange

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)


class StatementTransformation(Transformation):
    """
    Base class for all transformations that are applied to a statement.
    """
    @classmethod
    def all_at_lines(cls,
                     problem: Problem,
                     snippets: SnippetDatabase,
                     lines: List[FileLine],
                     *,
                     threads: int = 1
                     ) -> Dict[FileLine, Iterator[Transformation]]:
        return {line: cls.all_at_line(problem, snippets, line)
                for line in lines}

    @classmethod
    def all_at_line(cls,
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
            yield from cls.all_at_statement(problem, snippets, statement)

    @classmethod
    def all_at_statement(cls,
                         problem: Problem,
                         snippets: SnippetDatabase,
                         statement: kaskara.Statement
                         ) -> Iterator[Transformation]:
        """
        Returns an iterator over all of the possible transformations of this
        kind that can be performed at a given statement.
        """
        raise NotImplementedError


@register("DeleteStatement")
@attr.s(frozen=True, repr=False)
class DeleteStatement(StatementTransformation):
    location = attr.ib(type=FileLocationRange)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> 'Transformation':
        location = FileLocationRange.from_string(d['location'])
        return DeleteStatement(location)

    def _to_dict(self) -> Dict[str, Any]:
        return {'location': str(self.location)}

    def __repr__(self) -> str:
        s = "DeleteStatement<{}>".format(str(self.location))
        return s

    def to_replacement(self, problem: Problem) -> Replacement:
        return Replacement(self.location, '')

    @classmethod
    def all_at_statement(cls,
                         problem: Problem,
                         snippets: SnippetDatabase,
                         statement: kaskara.Statement
                         ) -> Iterator[Transformation]:
        yield DeleteStatement(statement.location)


@register("ReplaceStatement")
@attr.s(frozen=True, repr=False)
class ReplaceStatement(StatementTransformation):
    location = attr.ib(type=FileLocationRange)
    replacement = attr.ib(type=Snippet)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> 'Transformation':
        location = FileLocationRange.from_string(d['location'])
        replacement = Snippet.from_dict(d['replacement'])
        return ReplaceStatement(location, replacement)

    def _to_dict(self) -> Dict[str, Any]:
        return {'location': str(self.location),
                'replacement': self.replacement.to_dict()}

    def __repr__(self) -> str:
        s = "ReplaceStatement[{}]<{}>"
        s = s.format(str(self.replacement), str(self.location))
        return s

    def to_replacement(self, problem: Problem) -> Replacement:
        return Replacement(self.location, str(replacement))

    @classmethod
    def all_at_statement(cls,
                         problem: Problem,
                         snippets: SnippetDatabase,
                         statement: kaskara.Statement
                         ) -> Iterator[Transformation]:
        filename = statement.location.filename
        snippets = snippets.in_file(filename)

        # FIXME filter snippets

        for snippet in snippets:
            yield ReplaceStatement(statement.location, snippet)


@register("InsertStatement")
@attr.s(frozen=True, repr=False)
class InsertStatement(StatementTransformation):
    location = attr.ib(type=FileLocation)
    statement = attr.ib(type=Snippet)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> 'Transformation':
        location = FileLocation.from_string(d['location'])
        statement = Snippet.from_dict(d['snippet'])
        return InsertStatement(location, statement)

    def _to_dict(self) -> Dict[str, Any]:
        return {'location': str(self.location),
                'statement': self.statement.to_dict()}

    def __repr__(self) -> str:
        s = "InsertStatement[{}]<{}>"
        s = s.format(str(self.location), str(self.statement.content))
        return s

    def to_replacement(self, problem: Problem) -> Replacement:
        r = FileLocationRange(self.location.filename,
                              LocationRange(self.location.location, self.location.location))
        return Replacement(r, self.statement.content)

    @classmethod
    def all_at_line(cls,
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
            logger.warning("cannot determine statement insertions: no Kaskara analysis found")  # noqa: pycodestyle
            yield from []  # TODO this is redundant?
            return

        points = analysis.insertions.at_line(line)  # type: Iterator[kaskara.InsertionPoint]  # noqa: pycodestyle
        for point in points:
            yield from cls.all_at_point(problem, snippets, point)

    @classmethod
    def should_insert_at_location(cls,
                                  problem: Problem,
                                  location: FileLocation
                                  ) -> bool:
        """
        Determines whether an insertion of this kind should be made at a given
        location.
        """
        if not problem.analysis:
            return True
        if not problem.analysis.is_inside_function(location):
            return False
        return True

    @classmethod
    def viable_snippets(cls,
                        problem: Problem,
                        snippets: SnippetDatabase,
                        point: kaskara.InsertionPoint
                        ) -> Iterator[Snippet]:
        """
        Returns an iterator over the set of snippets that can be used as
        viable insertions at a given insertion point.
        """
        filename = point.location.filename
        yield from snippets.in_file(filename)

    # FIXME use all_at_statement
    @classmethod
    def all_at_point(cls,
                     problem: Problem,
                     snippets: SnippetDatabase,
                     point: kaskara.InsertionPoint
                     ) -> Iterator[Transformation]:
        """
        Returns an iterator over all of the transformations of this kind that
        can be performed at a given insertion point.
        """
        location = point.location
        if not cls.should_insert_at_location(problem, location):
            return
        viable_snippets = list(cls.viable_snippets(problem, snippets, point))
        # logger.info("VIABLE SNIPPETS AT POINT [%s]: %s",
        #             point, [s.content for s in viable_snippets])
        for snippet in cls.viable_snippets(problem, snippets, point):
            if snippet.reads.issubset(point.visible):
                yield cls(location, snippet)
            # else:
            #     logger.debug("skipping snippet [%s]: failed scope analysis.",
            #                  snippet.content)
