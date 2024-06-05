import abc
import typing as t
from collections.abc import Iterator, Sequence
from typing import Generic, TypeVar

from ..container import ProgramContainer
from ..core import Test, TestOutcome
from ..environment import Environment

T = TypeVar("T", bound=Test)


class TestSuite(Generic[T]):
    _environment: Environment

    def __init__(self, environment: Environment, tests: Sequence[T]) -> None:
        self.__name_to_test = {t.name: t for t in tests}
        self._environment = environment

    def __len__(self) -> int:
        return len(self.__name_to_test)

    def __iter__(self) -> Iterator[Test]:
        yield from self.__name_to_test.values()

    def __getitem__(self, name: str) -> Test:
        return self.__name_to_test[name]

    @abc.abstractmethod
    def execute(
        self,
        container: ProgramContainer,
        test: T,
        *,
        coverage: bool = False,
        environment: t.Optional[t.Mapping[str, str]] = None,
    ) -> TestOutcome:
        """Executes a given test inside a container.

        Parameters
        ----------
        container: ProgramContainer
            The container in which the test should be executed.
        test: T
            The test that should be executed.
        coverage: bool
            If :code:`True`, the test harness will be instructed to run the
            test in coverage collection mode. If no such mode is supported,
            the test will be run as usual.
        environment: Mapping[str, str], optional
            An optional set of environment variables that should be used when
            executing the test.

        Returns
        -------
        TestOutcome
            A concise summary of the test execution.
        """
        raise NotImplementedError
