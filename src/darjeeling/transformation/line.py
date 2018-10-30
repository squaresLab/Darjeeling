"""
This module implements GenProg-style operators for individual source code
lines.
"""
__all__ = [
#    'PrependLine',
    'DeleteLine'
#    'ReplaceLine',
#    'SwapLines'
]

from typing import List, Iterator, Iterable, Dict, Any, FrozenSet
import logging

import attr

from .base import Transformation, register
from ..problem import Problem
from ..snippet import Snippet, SnippetDatabase
from ..core import Replacement, FileLine, FileLocationRange, FileLocation, \
                   FileLineSet, Location, LocationRange

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)


class LineTransformation(Transformation):
    """
    Base class for all line-based transformations.
    """
    @classmethod
    def all_at_lines(cls,
                     problem: Problem,
                     snippets: SnippetDatabase,
                     lines: List[FileLine],
                     *,
                     threads: int = 1
                     ) -> Dict[FileLine, Iterator[Transformation]]:
        return {l: cls.all_at_line(problem, snippets, l) for l in lines}

    @classmethod
    def all_at_line(cls,
                    problem: Problem,
                    snippets: SnippetDatabase,
                    line: FileLine
                    ) -> Iterator[Transformation]:
        raise NotImplementedError


@register("delete-line")
@attr.s(frozen=True)
class DeleteLine(LineTransformation):
    line = attr.ib(type=FileLine)

    @classmethod
    def all_at_line(cls, problem, snippets, line):
        yield DeleteLine(line)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> 'Transformation':
        location = FileLine.from_string(d['line'])
        return DeleteStatement(location)

    def _to_dict(self) -> Dict[str, Any]:
        return {'line': str(self.line)}

    def to_replacement(self, problem: Problem) -> Replacement:
        loc = problem.sources.line_to_location_range(self.line)
        return Replacement(loc, '')
