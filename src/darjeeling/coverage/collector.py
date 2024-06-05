from __future__ import annotations

__all__ = ("CoverageCollector",)

import abc
from collections.abc import Mapping
from typing import Any, Optional, final

from loguru import logger

from .. import exceptions as exc
from ..container import ProgramContainer
from ..core import FileLineSet, TestCoverage, TestCoverageMap
from ..environment import Environment
from ..program import ProgramDescription
from ..util import dynamically_registered


@dynamically_registered(lookup="lookup", length=None, iterator=None)
class CoverageCollectorConfig(abc.ABC):
    """Describes a means of collecting test suite coverage."""
    @classmethod
    def lookup(cls, name: str) -> type[CoverageCollectorConfig]:
        raise NotImplementedError

    @classmethod
    def from_dict(cls,
                  dict_: Mapping[str, Any],
                  dir_: Optional[str] = None,
                  ) -> CoverageCollectorConfig:
        if "type" not in dict_:
            m = 'missing expected property: "type"'
            raise exc.BadConfigurationException(m)
        type_name: str = dict_["type"]
        type_: type[CoverageCollectorConfig] = \
            CoverageCollectorConfig.lookup(type_name)
        return type_.from_dict(dict_, dir_)

    @abc.abstractmethod
    def build(
        self,
        environment: Environment,
        program: ProgramDescription,
    ) -> CoverageCollector:
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

    @final
    def collect(self) -> TestCoverageMap:
        """Computes coverage for a given program."""
        test_to_coverage: dict[str, TestCoverage] = {}
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
                logger.trace(f"executed test for coverage: {outcome}")
                lines = self._extract(container)
                logger.trace(f"lines covered by test [{test}]: {lines}")
                test_coverage = TestCoverage(test=test.name,
                                             outcome=outcome,
                                             lines=lines)
                test_to_coverage[test.name] = test_coverage
        return TestCoverageMap(test_to_coverage)
