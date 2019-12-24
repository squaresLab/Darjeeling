# -*- coding: utf-8 -*-
from typing import (Sequence, Iterator, TypeVar, Dict, Any, Sequence, Generic,
                    Type, ClassVar, Optional)
import abc

import attr
import bugzoo

from ..core import TestOutcome, Test
from ..config import TestSuiteConfig
from ..container import ProgramContainer
from ..environment import Environment
from ..util import dynamically_registered

T = TypeVar('T', bound=Test)
C = TypeVar('C', bound=TestSuiteConfig)


@dynamically_registered('CONFIG', length=None, iterator=None,
                        lookup='_for_config_type')
class TestSuite(Generic[T, C]):
    CONFIG: ClassVar[Type[C]]
    _environment: Environment

    def __init__(self, environment: Environment, tests: Sequence[T]) -> None:
        self.__name_to_test = {t.name: t for t in tests}
        self._environment = environment

    @staticmethod
    def _for_config_type(type_config: Type[TestSuiteConfig]
                        ) -> Type['TestSuite']:
        """Fetches the TestSuite class for a given TestSuiteConfig class."""
        ...

    @classmethod
    @abc.abstractmethod
    def from_config(cls,
                    cfg: C,
                    environment: Environment,
                    bug: bugzoo.Bug
                    ) -> 'TestSuite':
        type_ = TestSuite._for_config_type(cfg.__class__)
        return type_.from_config(cfg, environment, bug)

    def __len__(self) -> int:
        return len(self.__name_to_test)

    def __iter__(self) -> Iterator[Test]:
        yield from self.__name_to_test.values()

    def __getitem__(self, name: str) -> Test:
        return self.__name_to_test[name]

    @abc.abstractmethod
    def execute(self,
                container: ProgramContainer,
                test: T,
                *,
                coverage: bool = False
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

        Returns
        -------
        TestOutcome
            A concise summary of the test execution.
        """
        raise NotImplementedError
