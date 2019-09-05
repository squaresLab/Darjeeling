__all__ = ('Replacement', 'FileLine', 'FileLocationRange', 'Location',
           'TestCoverage', 'TestCoverageMap')

from typing import (TypeVar, Sequence, Iterator, Optional, Dict, Generic, Set)
from collections import OrderedDict
from enum import Enum
import abc

import attr
from bugzoo import Container
from bugzoo import Client as BugZooClient
from boggart.core.replacement import Replacement
from boggart.core.location import FileLocationRange, FileLine, Location, \
                                  LocationRange, FileLocation, FileLineSet

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


@attr.ib(frozen=True, slots=True)
class TestCoverage(Set[FileLine]):
    """Describes the lines that were executed during a given test execution."""
    test: str = attr.ib()
    outcome: TestOutcome = attr.ib()
    lines: Set[FileLine] = attr.ib()

    def __contains__(self, elem: object) -> bool:
        return elem in self.lines

    def __iter__(self) -> Iterator[FileLine]:
        yield from self.lines

    def __contains__(self, l: FileLine) -> bool:
        return l in self.lines


class TestCoverageMap(Mapping[str, TestCoverage]):
    """Contains coverage information for each test within a test suite."""
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
    def passing(self) -> TestCoverageMap:
        """Returns a variant of this mapping restricted to passing tests."""
        contents = {name: coverage for (name, coverage) in self.__mapping
                    if coverage.outcome.successful}
        return TestCoverageMap(contents)

    @property
    def locations(self) -> Set[FileLine]:
        """Returns the set of all locations that are covered in this map."""
        if not self.__mapping:
            return FileLineSet()
        coverage_locations = self.__mapping.values()
        return coverage_locations[0].union(coverage_locations[1:])
