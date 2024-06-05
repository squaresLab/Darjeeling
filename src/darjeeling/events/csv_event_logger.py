__all__ = ("CsvEventLogger",)

import csv
import os
import typing
from collections.abc import Sequence
from typing import Optional, TextIO

import attr
from typing_extensions import Protocol

from .event import (
    BuildFinished,
    BuildStarted,
    CandidateEvaluationError,
    CandidateEvaluationFinished,
    CandidateEvaluationStarted,
    DarjeelingEvent,
    TestExecutionFinished,
    TestExecutionStarted,
)
from .handler import DarjeelingEventHandler

if typing.TYPE_CHECKING:
    from ..problem import Problem


class _CSVWriter(Protocol):
    def writerow(self, row: Sequence[str]) -> None:
        ...


@attr.s(eq=False, hash=False)
class CsvEventLogger(DarjeelingEventHandler):
    """Logs all events to a CSV file.

    Attributes
    ----------
    filename: str
        The absolute path to the file to which events should be relayed.
    """
    filename: str = attr.ib()
    problem: "Problem" = attr.ib()
    _file: TextIO = attr.ib(init=False, repr=False)
    _writer: _CSVWriter = attr.ib(init=False, repr=False)

    @filename.validator
    def validate_filename(self, attr, value) -> None:  # type: ignore
        if not os.path.isabs(self.filename):
            raise ValueError("'filename' must be an absolute path")

    def __attrs_post_init__(self) -> None:
        self._file = open(self.filename, "w")
        self._writer = csv.writer(self._file, delimiter="ɛ")

    def _write(self, row: Sequence[str]) -> None:
        row = [s.replace("\n", "\\n") for s in row]
        self._writer.writerow(row)
        self._file.flush()

    def _event_to_row(self,
                      event: DarjeelingEvent,
                      ) -> Optional[Sequence[str]]:
        """Transforms an event to a CSV row."""
        if isinstance(event, CandidateEvaluationStarted):
            diff = str(event.candidate.to_diff())
            return ["CANDIDATE", event.candidate.id, diff]
        if isinstance(event, CandidateEvaluationError):
            diff = str(event.candidate.to_diff())
            return ["CANDIDATE-ERROR", event.candidate.id, diff,
                    str(event.error)]
        if isinstance(event, CandidateEvaluationFinished):
            diff = str(event.candidate.to_diff())
            is_repair = event.outcome.is_repair
            return ["PATCH-ACCEPTED" if is_repair else "PATCH-REJECTED",
                    event.candidate.id, diff]
        if isinstance(event, BuildStarted):
            return ["BUILD-STARTED", event.candidate.id]
        if isinstance(event, BuildFinished):
            status = "passed" if event.outcome.successful else "failed"
            duration = f"{event.outcome.time_taken:.3f}"
            return ["BUILD-OUTCOME", event.candidate.id, status, duration]
        if isinstance(event, TestExecutionStarted):
            return ["TEST-STARTED", event.candidate.id, event.test.name]
        if isinstance(event, TestExecutionFinished):
            status = "passed" if event.outcome.successful else "failed"
            duration = f"{event.outcome.time_taken:.3f}"
            return ["TEST-OUTCOME", event.candidate.id, event.test.name,
                    status, duration]
        return None

    def notify(self, event: DarjeelingEvent) -> None:
        row = self._event_to_row(event)
        if row:
            self._write(row)
