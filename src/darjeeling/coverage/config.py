from __future__ import annotations

__all__ = ("CoverageConfig",)

import os
import typing as t
from typing import Any, Optional

import attr
from loguru import logger

from .. import exceptions as exc
from ..core import FileLine, FileLineSet, TestCoverageMap
from .collector import CoverageCollectorConfig

if t.TYPE_CHECKING:
    from ..environment import Environment
    from ..program import ProgramDescription


@attr.s(frozen=True)
class CoverageConfig:
    """Holds instructions for collecting and processing coverage.

    Attributes
    ----------
    collector_config: CoverageCollectorConfig
        The configuration that should be used to instrument the program and
        to collect coverage.
    restrict_to_files: Set[str], optional
        An optional set of files to which coverage should be restricted.
    restrict_to_lines: Set[FileLine], optional
        An optional set of lines to which coverage should be restricted.
    load_from_file: str, optional
        The name of the file, if any, that coverage information should be
        read from.

    Raises
    ------
    ValueError
        If coverage is restricted to the empty set of files.
    """
    collector_config: CoverageCollectorConfig = attr.ib()
    restrict_to_files: frozenset[str] | None = attr.ib(default=None)
    restrict_to_lines: t.AbstractSet[FileLine] | None = attr.ib(default=None)
    load_from_file: str | None = attr.ib(default=None)

    @restrict_to_files.validator
    def validate_restrict_to_files(self, attr, value) -> None:  # type: ignore
        if value is None:
            return
        if not value:
            raise ValueError("cannot restrict to empty set of files")

    @restrict_to_lines.validator
    def validate_restrict_to_lines(self, attr, value) -> None:  # type: ignore
        if value is None:
            return
        if not value:
            raise ValueError("cannot restrict to empty set of lines")

    @classmethod
    def from_dict(
        cls,
        d: dict[str, Any],
        dir_: Optional[str] = None,
    ) -> CoverageConfig:
        restrict_to_files: Optional[frozenset[str]] = None
        restrict_to_lines: t.AbstractSet[FileLine] | None = None
        load_from_file: str | None = None
        if "load-from-file" in d:
            load_from_file = d["load-from-file"]
            assert load_from_file is not None
            if not os.path.isabs(load_from_file):
                assert dir_ is not None
                load_from_file = os.path.join(dir_, load_from_file)
        if "restrict-to-files" in d:
            restrict_to_files_list: list[str] = d["restrict-to-files"]
            restrict_to_files = frozenset(restrict_to_files_list)
        if "restrict-to-lines" in d:
            restrict_to_lines = FileLineSet.from_dict(d["restrict-to-lines"])

        if "method" not in d:
            m = "missing expected section [method] in coverage section"
            raise exc.BadConfigurationException(m)
        collector_config = \
            CoverageCollectorConfig.from_dict(d["method"], dir_)

        return CoverageConfig(
            collector_config=collector_config,
            restrict_to_files=restrict_to_files,
            restrict_to_lines=restrict_to_lines,
            load_from_file=load_from_file,
        )

    def build(
        self,
        environment: Environment,
        program: ProgramDescription,
    ) -> TestCoverageMap:
        """Follows the instructions in this config to obtain coverage."""
        coverage: TestCoverageMap

        if self.load_from_file:
            fn_coverage = self.load_from_file
            logger.info(f"loading coverage from file: {fn_coverage}")
            coverage = TestCoverageMap.from_file(fn_coverage)
        else:
            collector = self.collector_config.build(environment, program)
            coverage = collector.collect()

        if self.restrict_to_files:
            coverage = coverage.restrict_to_files(self.restrict_to_files)

        if self.restrict_to_lines:
            coverage = coverage.restrict_to_locations(self.restrict_to_lines)

        return coverage
