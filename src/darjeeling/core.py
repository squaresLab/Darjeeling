__all__ = ('Replacement', 'FileLine', 'FileLocationRange', 'Location',
           'TestCoverage', 'TestCoverageMap')

from typing import (TypeVar, Sequence, Iterator, Optional, Dict, Generic, Set,
                    Mapping, Iterable)
from collections import OrderedDict
from enum import Enum
import abc

import attr
from bugzoo.core import TestSuiteCoverage as BugZooTestSuiteCoverage
from bugzoo.core import TestCoverage as BugZooTestCoverage
from bugzoo.core import TestOutcome as BugZooTestOutcome
from bugzoo import Container
from bugzoo import Client as BugZooClient
from bugzoo.core import FileLine, FileLineMap, FileLineSet
from boggart.core.replacement import Replacement
from boggart.core.location import (FileLocationRange,
                                   Location, LocationRange, FileLocation)

from .exceptions import LanguageNotSupported

class Language(Enum):
    @classmethod
    def find(cls, name: str) -> 'Language':
        try:
            return next(l for l in cls if l.value == name)
        except StopIteration:
            raise LanguageNotSupported(name)

    C = 'c'
    CPP = 'cpp'
    TEXT = 'text'


class Test:
    """An individual test case for the program under repair."""
    @property
    @abc.abstractmethod
    def name(self) -> str:
        """A unique name for the test case."""
        raise NotImplementedError


@attr.s(frozen=True, slots=True)
class TestOutcome:
    """Records the outcome of a test execution."""
    successful = attr.ib(type=bool)
    time_taken = attr.ib(type=float)

    @staticmethod
    def from_bugzoo(outcome: BugZooTestOutcome) -> 'TestOutcome':
        return TestOutcome(successful=outcome.passed,
                           time_taken=outcome.duration)


@attr.s(frozen=True, slots=True)
class BuildOutcome:
    """Records the outcome of a build attempt."""
    successful = attr.ib(type=bool)
    time_taken = attr.ib(type=float)


class TestOutcomeSet(object):
    """Records the outcome of different test executions for a single patch."""
    def __init__(self,
                 outcomes: Optional[Dict[str, TestOutcome]] = None
                 ) -> None:
        if outcomes is None:
            outcomes = {}
        self.__outcomes = outcomes # type: Dict[str, TestOutcome]

    def __iter__(self) -> Iterator[str]:
        return self.__outcomes.keys().__iter__()

    def __getitem__(self, test: str) -> TestOutcome:
        return self.__outcomes[test]

    def with_outcome(self, test: str, outcome: TestOutcome) -> 'TestOutcomeSet':
        outcomes = self.__outcomes.copy()
        outcomes[test] = outcome
        return TestOutcomeSet(outcomes)

    def merge(self, other: 'TestOutcomeSet') -> 'TestOutcomeSet':
        outcomes = self.__outcomes.copy()
        for test_name in other:
            outcomes[test_name] = other[test_name]
        return TestOutcomeSet(outcomes)


T = TypeVar('T', bound=Test)


class TestSuite(Generic[T]):
    def __init__(self, bz: BugZooClient, tests: Sequence[T]) -> None:
        self.__name_to_test = {t.name: t for t in tests}
        self._bugzoo = bz

    def __len__(self) -> int:
        return len(self.__name_to_test)

    def __iter__(self) -> Iterator[Test]:
        yield from self.__name_to_test.values()

    def __getitem__(self, name: str) -> Test:
        return self.__name_to_test[name]

    @abc.abstractmethod
    def execute(self, container: Container, test: T) -> TestOutcome:
        raise NotImplementedError


@attr.s(frozen=True, slots=True)
class TestCoverage:
    """Describes the lines that were executed during a given test execution."""
    test: str = attr.ib()
    outcome: TestOutcome = attr.ib()
    lines: Set[FileLine] = attr.ib()

    @staticmethod
    def from_bugzoo(coverage: BugZooTestCoverage) -> 'TestCoverage':
        return TestCoverage(
            test=coverage.test,
            outcome=TestOutcome.from_bugzoo(coverage.outcome),
            lines=coverage.lines)

    def __contains__(self, elem: object) -> bool:
        return elem in self.lines

    def __iter__(self) -> Iterator[FileLine]:
        yield from self.lines

    def __len__(self) -> int:
        return len(self.lines)

    def restrict_to_files(self, files: Iterable[str]) -> 'TestCoverage':
        """Returns a variant of this coverage, restricted to given files."""
        lines = FileLineSet(l for l in self.lines if l.filename in files)
        return TestCoverage(self.test, self.outcome, lines)

    def restrict_to_locations(self,
                              locations: Iterable[FileLine]
                              ) -> 'TestCoverage':
        """
        Returns a variant of this coverage, restricted to given locations.
        """
        lines = self.lines.intersection(locations)
        return TestCoverage(self.test, self.outcome, lines)


class TestCoverageMap(Mapping[str, TestCoverage]):
    """Contains coverage information for each test within a test suite."""
    @staticmethod
    def from_bugzoo(coverage: BugZooTestSuiteCoverage) -> 'TestCoverageMap':
        return TestCoverageMap({test_name: TestCoverage.from_bugzoo(test_cov)
                                for (test_name, test_cov) in coverage.items()})

    def __init__(self, mapping: Mapping[str, TestCoverage]):
        self.__mapping: OrderedDict[str, TestCoverage] = OrderedDict()
        for test_name in sorted(mapping):
            self.__mapping[test_name] = mapping[test_name]

    def __len__(self) -> int:
        """Returns the number of tests represented in this map."""
        return len(self.__mapping)

    def __getitem__(self, name: str) -> TestCoverage:
        """Returns the coverage for a test given by its name."""
        return self.__mapping[name]

    def __iter__(self) -> Iterator[str]:
        """Returns an iterator over the names of the tests in this map."""
        yield from self.__mapping

    @property
    def passing(self) -> 'TestCoverageMap':
        """Returns a variant of this mapping restricted to passing tests."""
        contents = {name: coverage for (name, coverage)
                    in self.__mapping.items()
                    if coverage.outcome.successful}
        return TestCoverageMap(contents)

    @property
    def failing(self) -> 'TestCoverageMap':
        """Returns a variant of this mapping restricted to failing tests."""
        contents = {name: coverage for (name, coverage)
                    in self.__mapping.items()
                    if not coverage.outcome.successful}
        return TestCoverageMap(contents)

    @property
    def locations(self) -> Set[FileLine]:
        """Returns the set of all locations that are covered in this map."""
        locs: Set[FileLine] = FileLineSet()
        if not self.__mapping:
            return locs
        return locs.union(*self.values())

    def covering_tests(self, location: FileLine) -> Set[str]:
        """Returns the names of the tests that cover a given location."""
        return set(name for (name, cov) in self.__mapping.items()
                   if location in cov)

    def restrict_to_files(self, files: Iterable[str]) -> 'TestCoverageMap':
        """
        Returns a variant of this map that only contains coverage for a given
        set of files.
        """
        return TestCoverageMap({test: cov.restrict_to_files(files)
                                for (test, cov) in self.items()})

    def restrict_to_locations(self,
                              locations: Iterable[FileLine]
                              ) -> 'TestCoverageMap':
        """
        Returns a variant of this map with its coverage restricted to a given
        set of locations.
        """
        return TestCoverageMap({test: cov.restrict_to_locations(locations)
                                for (test, cov) in self.items()})

