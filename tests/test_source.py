# -*- coding: utf-8 -*-
import os
import tempfile

import pytest

from darjeeling.source import ProgramSource, ProgramSourceFile

SIMPLE_FILE_NAME = 'simple.py'
SIMPLE_FILE_CONTENTS = \
"""
@attr.s(frozen=True, slots=True)
class TestOutcome:
    \"\"\"Records the outcome of a test execution.\"\"\"
    successful = attr.ib(type=bool)
    time_taken = attr.ib(type=float)

    @staticmethod
    def from_bugzoo(outcome: BugZooTestOutcome) -> 'TestOutcome':
        return TestOutcome(name="???", successful=outcome.passed,
                           time_taken=outcome.duration,
                           output=None)

    @staticmethod
    def from_dict(d: Dict[str, Any], name:str=None) -> 'TestOutcome':
        if name is None:
            name = "???"
        return TestOutcome(d.get('name', name), d['successful'], 
                d['time-taken'], d.get('output', None))

    def to_dict(self) -> Dict[str, Any]:
        return {'successful': self.successful,
                'time-taken': self.time_taken}
""".strip()


@pytest.fixture
def simple_file():
    return ProgramSourceFile(SIMPLE_FILE_NAME, SIMPLE_FILE_CONTENTS)


def test_filename(simple_file):
    assert simple_file.filename == SIMPLE_FILE_NAME


def test_num_lines(simple_file):
    assert simple_file.num_lines == 18


def test_read_line(simple_file):
    read_line = simple_file.read_line
    assert read_line(2) == "class TestOutcome:"
    assert read_line(1) == "@attr.s(frozen=True, slots=True)"
    assert read_line(18) == "                'time-taken': self.time_taken}"
