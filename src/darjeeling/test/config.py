# -*- coding: utf-8 -*-
__all__ = ('TestSuiteConfig',)

from typing import Any, Dict, NoReturn, Optional, Type
import abc
import typing

from .. import exceptions as exc
from ..util import dynamically_registered

if typing.TYPE_CHECKING:
    from .base import TestSuite
    from ..environment import Environment


@dynamically_registered(lookup='lookup', length=None, iterator=None)
class TestSuiteConfig(abc.ABC):
    """Describes a test suite configuration."""
    @staticmethod
    def lookup(name: str) -> Type['TestSuiteConfig']:
        ...

    @classmethod
    @abc.abstractmethod
    def from_dict(cls,
                  d: Dict[str, Any],
                  dir_: Optional[str] = None
                  ) -> 'TestSuiteConfig':
        def err(message: str) -> NoReturn:
            message = f"bad test suite configuration section: {message}"
            raise exc.BadConfigurationException(message)

        if 'type' not in d:
            err('missing "type" property')
        if not isinstance(d['type'], str):
            err('"type" property must be a string')

        name_type: str = d['type']
        type_: Type[TestSuiteConfig] = TestSuiteConfig.lookup(name_type)
        return type_.from_dict(d, dir_)

    @abc.abstractmethod
    def build(self,
              environment: 'Environment'
              ) -> 'TestSuite':
        """Builds the test suite described by this configuration."""
        ...
