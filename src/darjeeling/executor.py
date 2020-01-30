# -*- coding: utf-8 -*-
__all__ = ('AnnotatedTestExecution', 'TestAnnotationExecutor')

import abc

from .core import TestOutcome


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


class TestAnnotationExecutor(abc.ABC):
    """Performs annotated test execution by collecting additional information
    about test executions."""
