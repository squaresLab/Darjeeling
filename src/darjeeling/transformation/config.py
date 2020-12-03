# -*- coding: utf-8 -*-
"""
This module provides a data structure for representing the configuration of
both individual transformation schemas and the overall space of transformations
that is used by the search, as well as methods for loading/saving those
configurations to and from dictionary-based formats (e.g., JSON, YAML, TOML).
"""
__all__ = ('TransformationSchemaConfig', 'ProgramTransformationsConfig')

from typing import (Any, Collection, Iterator, List, Mapping, NoReturn,
                    Optional, Type)
import abc
import typing

import attr

from .transformations import ProgramTransformations
from .. import exceptions as exc
from ..snippet import SnippetDatabase
from ..util import dynamically_registered, tuple_from_iterable

if typing.TYPE_CHECKING:
    from .base import TransformationSchema
    from ..problem import Problem


@dynamically_registered(lookup='lookup')
class TransformationSchemaConfig(abc.ABC):
    """Describes a search algorithm configuration."""
    @staticmethod
    def __iter__() -> Iterator[str]:
        ...

    @staticmethod
    def __len__() -> int:
        ...

    @staticmethod
    def lookup(name: str) -> Type['TransformationSchemaConfig']:
        ...

    @classmethod
    @abc.abstractmethod
    def from_dict(cls,
                  d: Mapping[str, Any],
                  dir_: Optional[str] = None
                  ) -> 'TransformationSchemaConfig':
        name_type: str = d['type']
        type_: Type[TransformationSchemaConfig] = cls.lookup(name_type)
        return type_.from_dict(d, dir_)

    @abc.abstractmethod
    def build(self,
              problem: 'Problem',
              snippets: SnippetDatabase
              ) -> 'TransformationSchema':
        ...


@attr.s(frozen=True)
class ProgramTransformationsConfig:
    """Describes the configuration used to obtain the set of all possible
    transformations to the program under repair.

    Attributes
    ----------
    schemas: Collection[TransformationSchemaConfig]
        The configuration for each schema used to compose the space of
        possible transformations.
    """
    schemas: Collection[TransformationSchemaConfig] = \
        attr.ib(converter=tuple_from_iterable)

    @classmethod
    def from_dict(cls,
                  d: Mapping[str, Any],
                  dir_: Optional[str] = None
                  ) -> 'ProgramTransformationsConfig':
        def err(message: str) -> NoReturn:
            raise exc.BadConfigurationException(message)

        # load transformation schema configurations
        if 'schemas' not in d:
            err('missing "schemas" property in "transformations" section')
        if not isinstance(d['schemas'], list):
            err('illegal "schemas" property: should be a list')
        if not d['schemas']:
            err('illegal "schemas" property: '
                'must specify at least one schema')

        schemas: List[TransformationSchemaConfig] = []
        for d_schema in d['schemas']:
            schema = TransformationSchemaConfig.from_dict(d_schema, dir_)
            schemas.append(schema)

        return ProgramTransformationsConfig(schemas=schemas)

    def build(self,
              problem: 'Problem',
              snippets: SnippetDatabase,
              ) -> 'ProgramTransformations':
        """Constructs the transformation space described by this config."""
        schemas = [schema.build(problem, snippets) for schema in self.schemas]
        return ProgramTransformations.build(schemas, problem)
