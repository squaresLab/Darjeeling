# -*- coding: utf-8 -*-
"""
This module provides the base Transformation class, from which all
transformation schemas inherit.
"""
__all__ = ('Transformation', 'TransformationSchema')

from typing import (
    Collection,
    Dict,
    Generic,
    Iterator,
    Set,
    TypeVar,
)
import abc
import typing

from ..core import Replacement, FileLine

if typing.TYPE_CHECKING:
    from ..problem import Problem

T = TypeVar('T', bound='Transformation')


class Transformation(abc.ABC):
    """Represents a source code transformation.

    Attributes
    ----------
    line: FileLine
        The line at which this transformation is applied.
    """
    line: FileLine

    @abc.abstractmethod
    def to_replacement(self) -> Replacement:
        """Converts a transformation into a source code replacement."""
        ...

    @property
    @abc.abstractmethod
    def schema(self) -> 'TransformationSchema':
        """The schema that was used to produce this transformation."""
        ...


class TransformationSchema(Generic[T], abc.ABC):
    """
    Represents a form of syntactic transformation that can be applied to the
    program under repair. Sometimes referred to as a repair operator in the
    search-based program repair literature.
    """
    @abc.abstractmethod
    def find_all_in_file(self, filename: str) -> Iterator[Transformation]:
        """
        Finds all transformations using this schema that can be performed
        within a given file.
        """
        ...

    def find_all_at_lines_in_file(self,
                                  filename: str,
                                  lines: Collection[int]
                                  ) -> Iterator[Transformation]:
        """
        Finds all transformations using this schema that can be performed
        at a given set of lines within a specified file.
        """
        for transformation in self.find_all_in_file(filename):
            if transformation.line.num in lines:
                yield transformation

    def find_all_at_lines(self,
                          lines: Collection[FileLine],
                          ) -> Iterator[Transformation]:
        """
        Finds all transformations using this schema that can be performed
        at a given set of lines.
        """
        filename_to_lines: Dict[str, Set[int]] = {}
        for line in lines:
            filename = line.filename
            if filename not in filename_to_lines:
                filename_to_lines[filename] = set()
            filename_to_lines[filename].add(line.num)

        for filename, line_numbers in filename_to_lines.items():
            yield from self.find_all_at_lines_in_file(filename, line_numbers)

    def find_all(self, problem: 'Problem') -> Iterator[Transformation]:
        """Finds all transformations using this schema for a given problem."""
        implicated_lines = list(problem.localization)
        yield from self.find_all_at_lines(implicated_lines)
