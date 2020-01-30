# -*- coding: utf-8 -*-
__all__ = ('AnnotatedTestExecution', 'AnnotatedTestExecutor')

from typing import Generic, TypeVar
import abc
import typing

import attr

from ..core import FileLineSet, Test, TestOutcome
from ..container import ProgramContainer
from ..program import Program

T = TypeVar('T', bound='AnnotatedTestExecution')


class AnnotatedTestExecution(abc.ABC):
    """Provides additional information for a test execution in the form of an
    annotation.
    
    Attributes
    ----------
    outcome: TestOutcome
        The unannotated outcome of the test execution.
    """
    @property
    @abc.abstractmethod
    def outcome(self) -> TestOutcome:
        ...

    @property
    def successful(self) -> bool:
        """Indicates whether or not the test passed."""
        return self.test_outcome.successful

    @property
    def time_taken(self) -> float:
        """The number of seconds taken to execute the test."""
        return self.test_outcome.time_taken


class AnnotatedTestExecutor(Generic[T], abc.ABC):
    """Performs annotated test execution for a given container by collecting
    additional information during test execution. This capability can be used,
    for example, to collect coverage, invariants, and symbolic information.
    """
    @classmethod
    @abc.abstractmethod
    def build(self, container: ProgramContainer) -> None:
        """Builds an annotated test executor for a given container."""
        ...

    @abc.abstractmethod
    def container(self) -> ProgramContainer:
        """The container to which this executor is attached."""
        ...

    def program(self) -> Program:
        """A description of the program associated with this executor."""
        return self.container.program

    @abc.abstractmethod
    def execute(self, test: Test) -> T:
        """Executes a given test with annotation.

        Returns
        -------
        T
            The result of the annotated test execution.
        """
        ...


@attr.s(slots=True)
class GCovTestExecutor(AnnotatedTestExecutor[TestCoverage]):
    container: ProgramContainer

    def __attrs_post_init__(self) -> None:
        # TODO apply instrumentation
        # TODO build program

    def execute(self, test: Test) -> TestCoverage:
        """Computes coverage for a given test case."""
        outcome = self.program.execute(test)
        lines_covered = self._extract()
        return TestCoverage(test.name, outcome, lines_covered)

    def _extract(self) -> FileLineSet:
        """Uses gcov to extract a summary of the executed lines of code."""
        files = self.container.filesystem
        shell = self.container.shell
        temporary_filename = files.mktemp()

        command = f'gcovr -o "{temporary_filename}" -x -d -r .'
        response = shell.check_output(command, cwd=self._source_directory)  # TODO: store source directory
        report_file_contents = files.read(temporary_filename)
        return self._parse_report_from_text(report_file_contents)
