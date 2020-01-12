# -*- coding: utf-8 -*-
"""
This module provides a data structure for representing the configuration of
transformation schemas, and for loading/saving those configurations to/from
dictionary-based formats (e.g., JSON, YAML, TOML).
"""
__all__ = ('TransformationSchemaConfig',)

from typing import Iterator, Type, Optional, Mapping, List, Any
import abc
import typing

from ..snippet import SnippetDatabase
from ..util import dynamically_registered

if typing.TYPE_CHECKING:
    from .base import TransformationSchema
    from ..environment import Environment
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
