from __future__ import annotations

__all__ = ("ClangCoverageCollector",)

import typing as t
from dataclasses import dataclass

from .collector import CoverageCollector, CoverageCollectorConfig

if t.TYPE_CHECKING:
    from ..container import ProgramContainer
    from ..environment import Environment
    from ..program import ProgramDescription


@dataclass(frozen=True)
class ClangCoverageCollectorConfig(CoverageCollectorConfig):
    NAME: t.ClassVar[str] = "clang"

    @classmethod
    def from_dict(
        cls,
        dict_: t.Mapping[str, t.Any],
        dir_: t.Optional[str] = None,
    ) -> CoverageCollectorConfig:
        assert dict_["type"] == "clang"
        raise NotImplementedError

    def build(
        self,
        environment: Environment,
        program: ProgramDescription,
    ) -> CoverageCollector:
        raise NotImplementedError


@dataclass(frozen=True)
class ClangCoverageCollector(CoverageCollector):
    program: ProgramDescription

    def _prepare(self, container: ProgramContainer) -> None:
        raise NotImplementedError
