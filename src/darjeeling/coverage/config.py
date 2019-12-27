# -*- coding: utf-8 -*-
__all__ = ('CoverageConfig',)

from typing import Set, FrozenSet, Optional, Any, Dict, List
import logging
import os
import typing

import attr

from ..container import ProgramContainer
from ..core import (FileLineSet, FileLine, TestCoverageMap, Test, TestCoverage,
                    TestOutcome)
from ..test import TestSuite

if typing.TYPE_CHECKING:
    from ..environment import Environment
    from ..program import ProgramDescription

logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@attr.s(frozen=True)
class CoverageConfig:
    """Holds instructions for collecting and processing coverage.

    Attributes
    ----------
    restrict_to_files: Set[str], optional
        An optional set of files to which coverage should be restricted.
    load_from_file: str, optional
        The name of the file, if any, that coverage information should be
        read from.

    Raises
    ------
    ValueError
        If coverage is restricted to the empty set of files.
    """
    restrict_to_files: Optional[FrozenSet[str]] = attr.ib(default=None)
    restrict_to_lines: Optional[Set[FileLine]] = attr.ib(default=None)
    load_from_file: Optional[str] = attr.ib(default=None)

    @restrict_to_files.validator
    def validate_restrict_to_files(self, attr, value) -> None:
        if value is None:
            return
        if not value:
            raise ValueError("cannot restrict to empty set of files")

    @restrict_to_lines.validator
    def validate_restrict_to_lines(self, attr, value) -> None:
        if value is None:
            return
        if not value:
            raise ValueError("cannot restrict to empty set of lines")

    @staticmethod
    def from_dict(d: Dict[str, Any],
                  dir_: Optional[str] = None
                  ) -> 'CoverageConfig':
        restrict_to_files: Optional[FrozenSet[str]] = None
        restrict_to_lines: Optional[Set[FileLine]] = None
        load_from_file: Optional[str] = None
        if 'load-from-file' in d:
            load_from_file = d['load-from-file']
            assert load_from_file is not None
            if not os.path.isabs(load_from_file):
                assert dir_ is not None
                load_from_file = os.path.join(dir_, load_from_file)
        if 'restrict-to-files' in d:
            restrict_to_files_list: List[str] = d['restrict-to-files']
            restrict_to_files = frozenset(restrict_to_files_list)
        if 'restrict-to-lines' in d:
            restrict_to_lines = FileLineSet.from_dict(d['restrict-to-lines'])
        return CoverageConfig(restrict_to_files=restrict_to_files,
                              restrict_to_lines=restrict_to_lines,
                              load_from_file=load_from_file)

    def _collect(self,
                 environment: 'Environment',
                 program: 'ProgramDescription'
                 ) -> TestCoverageMap:
        bz = environment.bugzoo
        snapshot = program.snapshot
        tests = program.tests
        with program.provision() as container:
            logger.debug("computing coverage for snapshot: %s", snapshot.name)
            logger.debug("instrumenting container for coverage...")
            bz.containers.instrument(container._bugzoo)
            logger.debug("instrumented container for coverage")

            name_to_coverage: Dict[str, TestCoverage] = {}
            for test in tests:
                logger.debug("computing coverage for test [%s]", test.name)
                outcome: TestOutcome = tests.execute(container, test, coverage=True)
                logger.debug("test outcome [%s]: %s", test.name, outcome)
                logger.debug("extracting coverage for test [%s]", test.name)
                lines: Set[FileLine] = bz.containers.extract_coverage(container._bugzoo)
                lines = FileLineSet.from_iter(lines)
                logger.debug("extracted coverage for test [%s]:\n%s", test.name, lines)
                test_coverage = TestCoverage(test=test.name, outcome=outcome, lines=lines)
                name_to_coverage[test.name] = test_coverage

            return TestCoverageMap(name_to_coverage)

    def build(self,
              environment: 'Environment',
              program: 'ProgramDescription'
              ) -> TestCoverageMap:
        """Follows the instructions in this config to obtain coverage."""
        coverage: TestCoverageMap

        if self.load_from_file:
            fn_coverage = self.load_from_file
            logger.info('loading coverage from file: %s', fn_coverage)
            coverage = TestCoverageMap.from_file(fn_coverage)
        else:
            coverage = self._collect(environment, program)

        if self.restrict_to_files:
            coverage = coverage.restrict_to_files(self.restrict_to_files)

        if self.restrict_to_lines:
            coverage = coverage.restrict_to_locations(self.restrict_to_lines)

        return coverage
