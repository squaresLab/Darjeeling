# -*- coding: utf-8 -*-
"""
This module provides the base Transformation class, from which all
transformation schemas inherit.
"""
__all__ = ('Transformation', 'register')

from typing import (Any, Dict, List, Type, Iterator, Callable, TypeVar,
                    Generic, ClassVar, Mapping)
import abc
import logging

from ..exceptions import NameInUseException, \
                         UnknownTransformationSchemaException
from ..problem import Problem
from ..snippet import SnippetDatabase
from ..core import Replacement, FileLine

logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

T = TypeVar('T', bound='Transformation')

_REGISTRY: Dict[str, Type['TransformationSchema']] = {}


class Transformation(abc.ABC):
    """Represents a source code transformation."""
    def to_replacement(self, problem: Problem) -> Replacement:
        """Converts a transformation into a source code replacement."""
        ...


class TransformationSchema(Generic[T], abc.ABC):
    NAME: ClassVar[str]

    @staticmethod
    def find(name: str) -> Type['TransformationSchema']:
        """
        Retrieves the transformation schema that is registered under a given
        name.

        Raises:
            KeyError: if no schema is found under that name.
        """
        return _REGISTRY[name]

    @staticmethod
    def schemas() -> Iterator[str]:
        """
        Returns an iterator over the names of the transformation schemas
        that have been registered.
        """
        yield from _REGISTRY

    @classmethod
    @abc.abstractmethod
    def build(cls,
              problem: Problem,
              snippets: SnippetDatabase,
              threads: int
              ) -> 'TransformationSchema':
        ...

    @abc.abstractmethod
    def all_at_lines(self,
                     lines: List[FileLine]
                     ) -> Mapping[FileLine, Iterator['Transformation']]:
        """
        Returns a dictionary from lines to streams of all the possible
        transformations of this type that can be performed at that line.
        """
        ...


def register(name: str
             ) -> Callable[[Type[TransformationSchema]],
                            Type[TransformationSchema]]:
    """
    Registers a given transformation schema under a provided name.

    Raises:
        NameInUseException: if the given name is being used by another
            transformation schema.
    """
    def decorator(schema: Type[TransformationSchema]
                 ) -> Type[TransformationSchema]:
        logger.debug("registering transformation schema [%s] under name [%s]",
                     schema, name)
        global _REGISTRY
        if name in _REGISTRY:
            raise NameInUseException

        _REGISTRY[name] = schema
        logger.debug("registered transformation schema [%s] under name [%s]",
                     schema, name)
        return schema

    return decorator
