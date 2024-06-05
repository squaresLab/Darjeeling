from __future__ import annotations

__all__ = ("CoveragePyCollector", "CoveragePyCollectorConfig")

import json
import typing
from collections.abc import Mapping
from typing import Any, ClassVar, Optional

import attr

from darjeeling.core import FileLineSet
from darjeeling.coverage.collector import CoverageCollector, CoverageCollectorConfig

if typing.TYPE_CHECKING:
    from darjeeling.container import ProgramContainer
    from darjeeling.environment import Environment
    from darjeeling.program import ProgramDescription


@attr.s(frozen=True)
class CoveragePyCollectorConfig(CoverageCollectorConfig):
    NAME: ClassVar[str] = "coverage.py"

    @classmethod
    def from_dict(cls,
                  dict_: Mapping[str, Any],
                  dir_: Optional[str] = None,
                  ) -> CoverageCollectorConfig:
        assert dict_["type"] == cls.NAME
        return CoveragePyCollectorConfig()

    def build(self,
              environment: Environment,
              program: ProgramDescription,
              ) -> CoverageCollector:
        return CoveragePyCollector(program=program)


@attr.s(frozen=True, slots=True, auto_attribs=True)
class CoveragePyCollector(CoverageCollector):
    program: ProgramDescription

    def _read_report_json(self, json_: Mapping[str, Any]) -> FileLineSet:
        filename_to_lines: dict[str, set[int]] = {}
        filename_to_json_report = json_["files"]
        for filename, file_json in filename_to_json_report.items():
            filename_to_lines[filename] = set(file_json["executed_lines"])
        return FileLineSet(filename_to_lines)

    def _read_report_text(self, text: str) -> FileLineSet:
        json_ = json.loads(text)
        return self._read_report_json(json_)

    def _extract(self, container: ProgramContainer) -> FileLineSet:
        files = container.filesystem
        shell = container.shell
        temporary_filename = files.mktemp()
        command = (f'coverage json -o {temporary_filename} '
                   '--omit="tests/* && coverage erase"')
        shell.check_call(command, cwd=self.program.source_directory)
        report_text = files.read(temporary_filename)
        return self._read_report_text(report_text)
