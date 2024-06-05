from __future__ import annotations

__all__ = ("SearcherConfig",)

import abc
import typing
from collections.abc import Iterator
from typing import Any, Optional

from ..util import dynamically_registered

if typing.TYPE_CHECKING:
    from ..problem import Problem
    from ..resources import ResourceUsageTracker
    from ..transformation import ProgramTransformations
    from .base import Searcher


@dynamically_registered(lookup="lookup")
class SearcherConfig(abc.ABC):
    """Describes a search algorithm configuration."""
    @classmethod
    def __iter__(cls) -> Iterator[str]:
        raise NotImplementedError

    @classmethod
    def __len__(cls) -> int:
        raise NotImplementedError

    @classmethod
    def lookup(cls, name: str) -> type[SearcherConfig]:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def from_dict(
        cls,
        d: dict[str, Any],
        dir_: Optional[str] = None,
    ) -> SearcherConfig:
        name_type: str = d["type"]
        type_: type[SearcherConfig] = SearcherConfig.lookup(name_type)
        return type_.from_dict(d, dir_)

    @abc.abstractmethod
    def build(
        self,
        problem: Problem,
        resources: ResourceUsageTracker,
        transformations: ProgramTransformations,
        *,
        threads: int = 1,
        run_redundant_tests: bool = False,
    ) -> Searcher:
        ...
