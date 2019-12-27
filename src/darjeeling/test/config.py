# -*- coding: utf-8 -*-
__all__ = ('TestSuiteConfig',)

from typing import Dict, Optional, Any, Type
import abc
import logging
import typing

import bugzoo

from ..util import dynamically_registered

if typing.TYPE_CHECKING:
    from .base import TestSuite
    from ..environment import Environment

logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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
        if 'type' not in d:
            logger.debug("using default BugZoo test suite")
            name_type = 'bugzoo'
        else:
            name_type = d['type']
        type_: Type[TestSuiteConfig] = TestSuiteConfig.lookup(name_type)
        return type_.from_dict(d, dir_)

    @abc.abstractmethod
    def build(self,
              environment: 'Environment',
              bug: bugzoo.Bug
              ) -> 'TestSuite':
        """Builds the test suite described by this configuration."""
        ...
