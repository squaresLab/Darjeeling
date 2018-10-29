"""
This module provides the base Transformation class, from which all
transformation schemas inherit.
"""
__all__ = ['Transformation', 'register']

from typing import Any, Dict, List, Type, Iterator, Callable
import logging

from ..exceptions import NameInUseException, \
                         UnknownTransformationSchemaException
from ..problem import Problem
from ..snippet import SnippetDatabase
from ..core import Replacement, FileLine

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)

"""
Maintains a registry of transformation schemas indexed by name.
"""
REGISTRY = {}  # type: Dict[str, Type[Transformation]]


class Transformation(object):
    """
    Represents a transformation to a source code file.
    """
    def to_replacement(self, problem: Problem) -> Replacement:
        """
        Converts a transformation into a concrete source code replacement.
        """
        raise NotImplementedError

    @staticmethod
    def find_schema(name: str) -> 'Type[Transformation]':
        """
        Retrieves the transformation schema that is registered under a given
        name.

        Raises:
            KeyError: if no schema is found under that name.
        """
        return REGISTRY[name]

    @staticmethod
    def schemas() -> Iterator[str]:
        """
        Returns an iterator over the names of the transformation schemas
        that have been registered.
        """
        yield from REGISTRY

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> 'Transformation':
        """
        Constructs a transformation from a dictionary-based description.

        Raises:
            SyntaxError: if the provided description is not well formed.
            UnknownTransformationSchemaException: if the schema used by the
                transformation has not been registered or does not exist.

        Returns:
            the transformation that corresponds to the given description.
        """
        try:
            kind = d['kind']
        except KeyError:
            msg = "expected 'kind' property in transformation description"
            raise SyntaxError(msg)

        try:
            schema = REGISTRY[kind]
        except KeyError:
            raise UnknownTransformationSchemaException(kind)

        return schema.from_dict(d)

    @classmethod
    def all_at_lines(cls,
                     problem: Problem,
                     snippets: SnippetDatabase,
                     lines: List[FileLine],
                     *,
                     threads: int = 1
                     ) -> Dict[FileLine, Iterator['Transformation']]:
        """
        Returns a dictionary from lines to streams of all the possible
        transformations of this type that can be performed at that line.
        """
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        d = self._to_dict()
        d['kind'] = self.__class__.NAME  # type: ignore
        return d

    def _to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError


def register(name: str
             ) -> Callable[[Type[Transformation]], Type[Transformation]]:
    """
    Registers a given transformation schema under a provided name.

    Raises:
        NameInUseException: if the given name is being used by another
            transformation schema.
    """
    def decorator(schema: Type[Transformation]) -> Type[Transformation]:
        logger.debug("registering transformation schema [%s] under name [%s]",
                     schema, name)
        global REGISTRY
        if name in REGISTRY:
            raise NameInUseException

        # TODO class must implement a "from_dict" method

        schema.NAME = name  # type: ignore
        REGISTRY[name] = schema  # type: ignore
        logger.debug("registered transformation schema [%s] under name [%s]",
                     schema, name)
        return schema

    return decorator
