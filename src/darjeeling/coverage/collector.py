# -*- coding: utf-8 -*-
__all__ = ('CoverageCollector',)

from typing import Any, Dict, Mapping, Optional, Type
from typing_extensions import final
import abc

from loguru import logger

from .. import exceptions as exc
from ..core import (
    FileLineSet,
    Test,
    TestCoverage,
    TestCoverageMap,
    TestOutcome,
)
from ..container import ProgramContainer
from ..environment import Environment
from ..program import ProgramDescription
from ..util import dynamically_registered


@dynamically_registered(lookup='lookup', length=None, iterator=None)
class CoverageCollectorConfig(abc.ABC):
    """Describes a means of collecting test suite coverage."""
    @staticmethod
    def lookup(name: str) -> Type['CoverageCollectorConfig']:
        ...

    @classmethod
    @abc.abstractmethod
    def from_dict(cls,
                  dict_: Mapping[str, Any],
                  dir_: Optional[str] = None
                  ) -> 'CoverageCollectorConfig':
        if 'type' not in dict_:
            m = 'missing expected property: "type"'
            raise exc.BadConfigurationException(m)
        type_name: str = dict_['type']
        type_: Type[CoverageCollectorConfig] = \
            CoverageCollectorConfig.lookup(type_name)
        return type_.from_dict(dict_, dir_)

    @abc.abstractmethod
    def build(self,
              environment: Environment,
              program: ProgramDescription
              ) -> 'CoverageCollector':
        ...


class CoverageCollector(abc.ABC):
    """Used to compute test suite coverage for a given program."""
    @property
    @abc.abstractmethod
    def program(self) -> ProgramDescription:
        """The program associated with this coverage collector."""
        ...

    @abc.abstractmethod
    def _extract(self, container: ProgramContainer) -> FileLineSet:
        """Extracts a summary of the lines that were covered from disk."""
        ...

    def _prepare(self, container: ProgramContainer) -> None:
        """Prepares a container for coverage collection."""
        return

    def _override_test_outcome(self, test: Test, outcome: TestOutcome) -> TestOutcome:
        """This method can be overridden by coverage collectors to force the outcome for a particular test"""
        return outcome

    @final
    def collect(self) -> TestCoverageMap:
        """Computes coverage for a given program."""
        test_to_coverage: Dict[str, TestCoverage] = {}
        logger.trace("collecting coverage")
        with self.program.provision() as container:
            logger.trace("provisioned container for coverage")
            self._prepare(container)
            logger.trace("prepared program for coverage collection")
            test_suite = self.program.tests
            logger.trace("collecting coverage for each test")
            for test in test_suite:
                logger.trace(f"executing test for coverage: {test}")
                outcome = test_suite.execute(container, test, coverage=True)
                outcome = self._override_test_outcome(test, outcome)
                logger.trace(f"executed test for coverage: {outcome}")
                lines = self._extract(container)
                logger.trace(f"lines covered by test [{test}]: {lines}")
                test_coverage = TestCoverage(test=test.name,
                                             outcome=outcome,
                                             lines=lines)
                test_to_coverage[test.name] = test_coverage
        return TestCoverageMap(test_to_coverage)
