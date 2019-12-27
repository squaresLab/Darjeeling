# -*- coding: utf-8 -*-
__all__ = ('SearcherConfig',)

import datetime

from typing import Dict, Optional, Any, Type, Iterator, List
import abc
import logging
import typing

from ..util import dynamically_registered

if typing.TYPE_CHECKING:
    from .base import Searcher
    from ..environment import Environment
    from ..problem import Problem
    from ..transformation import Transformation


@dynamically_registered(lookup='lookup')
class SearcherConfig(abc.ABC):
    """Describes a search algorithm configuration."""
    @staticmethod
    def __iter__() -> Iterator[str]:
        ...

    @staticmethod
    def __len__() -> int:
        ...

    @staticmethod
    def lookup(name: str) -> Type['SearcherConfig']:
        ...

    @classmethod
    @abc.abstractmethod
    def from_dict(cls,
                  d: Dict[str, Any],
                  dir_: Optional[str] = None
                  ) -> 'SearcherConfig':
        name_type: str = d['type']
        type_: Type[SearcherConfig] = SearcherConfig.lookup(name_type)
        return type_.from_dict(d, dir_)

    @abc.abstractmethod
    def build(self,
              problem: 'Problem',
              transformations: List['Transformation'],
              *,
              threads: int = 1,
              candidate_limit: Optional[int] = None,
              time_limit: Optional[datetime.timedelta] = None
              ) -> 'Searcher':
        ...
