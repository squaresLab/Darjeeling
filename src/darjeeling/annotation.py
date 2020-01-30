# -*- coding: utf-8 -*-
__all__ = ('AnnotatedTestExecution', 'TestAnnotationExecutor')

from typing import Generic, TypeVar
import abc
import typing

from .core import Test, TestOutcome
from .container import ProgramContainer

T = TypeVar('T', bound='AnnotatedTestExecution')


class AnnotatedTestExecution(abc.ABC):
    """Provides additional information for a test execution in the form of an
    annotation.
    
    Attributes
    ----------
    test_outcome: TestOutcome
        The unannotated outcome of the test execution.
    """
    @property
    @abc.abstractmethod
    def test_outcome(self) -> TestOutcome:
        ...

    @property
    def successful(self) -> bool:
        """Indicates whether or not the test passed."""
        return self.test_outcome.successful

    @property
    def time_taken(self) -> float:
        """The number of seconds taken to execute the test."""
        return self.test_outcome.time_taken


class TestAnnotationExecutor(Generic[T], abc.ABC):
    """Performs annotated test execution by collecting additional information
    about test executions. This capability can be used, for example, to
    collect coverage, invariants, and symbolic information.
    """
    @abc.abstractmethod
    def prepare(self, container: ProgramContainer) -> None:
        """Prepares a given container for annotated execution."""
        ...

    @abc.abstractmethod
    def execute(self, container: ProgramContainer, test: Test) -> T:
        """Executes a given test with annotation.

        Returns
        -------
        T
            The result of the annotated test execution.
        """
        ...
