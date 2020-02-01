# -*- coding: utf-8 -*-
"""
This module provides the base Transformation class, from which all
transformation schemas inherit.
"""
__all__ = ('Transformation', 'TransformationSchema')

from typing import Generic, Iterator, List, Mapping, TypeVar
import abc

from ..core import Replacement, FileLine

T = TypeVar('T', bound='Transformation')


class Transformation(abc.ABC):
    """Represents a source code transformation."""
    @abc.abstractmethod
    def to_replacement(self) -> Replacement:
        """Converts a transformation into a source code replacement."""
        ...

    @property
    @abc.abstractmethod
    def line(self) -> FileLine:
        """The line at which this transformation is applied."""
        ...

    @property
    @abc.abstractmethod
    def schema(self) -> 'TransformationSchema':
        """The schema that was used to produce this transformation."""
        ...


class TransformationSchema(Generic[T], abc.ABC):
    @abc.abstractmethod
    def all_at_lines(self,
                     lines: List[FileLine]
                     ) -> Mapping[FileLine, Iterator['Transformation']]:
        """
        Returns a mapping from lines to streams of all the possible
        transformations of this type that can be performed at that line.
        """
        ...
