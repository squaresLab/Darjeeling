# -*- coding: utf-8 -*-
__all__ = ('CoveragePyCollector', 'CoveragePyCollectorConfig')

from typing import FrozenSet, Mapping, Any, Set, Dict, Optional, ClassVar
import json
import logging
import os
import typing

import attr

from .collector import CoverageCollector, CoverageCollectorConfig
from ..core import FileLineSet

if typing.TYPE_CHECKING:
    from ..container import ProgramContainer
    from ..environment import Environment
    from ..program import ProgramDescription

logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@attr.s(frozen=True)
class CoveragePyCollectorConfig(CoverageCollectorConfig):
    NAME: ClassVar[str] = 'coverage.py'

    @classmethod
    def from_dict(cls,
                  dict_: Mapping[str, Any],
                  dir_: Optional[str] = None
                  ) -> 'CoverageCollectorConfig':
        assert dict_['type'] == cls.NAME
        return CoveragePyCollectorConfig()

    def build(self,
              environment: 'Environment',
              program: 'ProgramDescription'
              ) -> 'CoverageCollector':
        return CoveragePyCollector(program=program)


@attr.s(frozen=True, slots=True, auto_attribs=True)
class CoveragePyCollector(CoverageCollector):
    program: 'ProgramDescription'

    def _read_report_json(self, json_: Mapping[str, Any]) -> FileLineSet:
        filename_to_lines: Dict[str, Set[int]] = {}
        filename_to_json_report = json_['files']
        for filename, file_json in filename_to_json_report.items():
            filename_to_lines[filename] = set(file_json['executed_lines'])
        return FileLineSet(filename_to_lines)

    def _read_report_text(self, text: str) -> FileLineSet:
        json_ = json.loads(text)
        return self._read_report_json(json_)

    def _extract(self, container: 'ProgramContainer') -> FileLineSet:
        files = container.filesystem
        shell = container.shell
        temporary_filename = files.mktemp()
        command = (f'coverage json -o {temporary_filename} '
                    '--omit="tests/* && coverage erase"')
        response = shell.check_output(command,
                                      cwd=self.program.source_directory)
        report_text = files.read(temporary_filename)
        return self._read_report_text(report_text)
