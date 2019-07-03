__all__ = ['Replacement', 'FileLine', 'FileLocationRange', 'Location']

from typing import TypeVar, Sequence, Iterator, Optional, Dict
from enum import Enum
import abc

import attr
from bugzoo import Container
from bugzoo import Client as BugZooClient
from boggart.core.replacement import Replacement
from boggart.core.location import FileLocationRange, FileLine, Location, \
                                  LocationRange, FileLocation, FileLineSet

from .exceptions import LanguageNotSupported

T = TypeVar('T')


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
    @property
    @abc.abstractmethod
    def name(self) -> str:
        raise NotImplementedError


@attr.s(frozen=True)
class TestOutcome(object):
    """Records the outcome of a test execution."""
    successful = attr.ib(type=bool)
    time_taken = attr.ib(type=float)


@attr.s(frozen=True)
class BuildOutcome(object):
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


class TestSuite:
    def __init__(self, bz: BugZooClient, tests: Sequence[T]) -> None:
        self.__name_to_test = {t.name for t in tests}
        self._bugzoo = bz

    def __len__(self) -> int:
        return len(self.__tests)

    def __iter__(self) -> Iterator[Test]:
        yield from self.__name_to_test.values()

    def __getitem__(self, name: str) -> Test:
        return self.__name_to_test[name]

    @abc.abstractmethod
    def execute(self, container: Container, test: T) -> TestOutcome:
        raise NotImplementedError
