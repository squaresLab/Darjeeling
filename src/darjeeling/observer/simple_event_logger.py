# -*- coding: utf-8 -*-
__all__ = ('SimpleEventLogger',)

from typing import Tuple, Optional, TextIO, Sequence
from typing_extensions import Protocol
import csv
import functools
import io
import os

import attr

from .observer import SearchObserver
from ..core import Test, TestOutcome, BuildOutcome
from ..candidate import Candidate
from ..outcome import CandidateOutcome


class _CSVWriter(Protocol):
    def writerow(self, row: Sequence[str]) -> None:
        ...


@attr.s(eq=False, hash=False)
class SimpleEventLogger(SearchObserver):
    """Logs search events to a CSV file.

    Attributes
    ----------
    filename: str
        The absolute path to the file to which events should be logged.
    """
    filename: str = attr.ib()
    _file: TextIO = attr.ib(init=False, repr=False)
    _writer: _CSVWriter = attr.ib(init=False, repr=False)

    @filename.validator
    def validate_filename(self, attr, value) -> None:
        if not os.path.isabs(self.filename):
            raise ValueError("'filename' must be an absolute path")

    def __attrs_post_init__(self) -> None:
        self._file = open(self.filename, 'w')
        self._writer = csv.writer(self._file)

    def close(self) -> None:
        self._file.close()

    def _write(self, row: Sequence[str]) -> None:
        self._writer.writerow(row)
        self._file.flush()

    def on_test_finished(self,
                         candidate: Candidate,
                         test: Test,
                         outcome: TestOutcome
                         ) -> None:
        status = 'passed' if outcome.successful else 'failed'
        duration = f'{outcome.time_taken:.3f}'
        row: Tuple[str, ...] = \
            ('TEST-OUTCOME', candidate.id, test.name, status, duration)
        self._write(row)

    def on_test_started(self, candidate: Candidate, test: Test) -> None:
        self._write(('TEST-STARTED', candidate.id, test.name))

    def on_build_started(self, candidate: Candidate) -> None:
        self._write(('BUILD-STARTED', candidate.id))

    def on_build_finished(self,
                          candidate: Candidate,
                          outcome: BuildOutcome
                          ) -> None:
        status = 'passed' if outcome.successful else 'failed'
        duration = f'{outcome.time_taken:.3f}'
        row: Tuple[str, ...] = \
            ('BUILD-OUTCOME', candidate.id, status, duration)
        self._write(row)

    def on_candidate_started(self, candidate: Candidate) -> None:
        # FIXME add diff!
        diff = "FIXMEFIXMEFIXME"
        self._write(('CANDIDATE-STARTED', candidate.id, diff))

    def on_candidate_finished(self,
                              candidate: Candidate,
                              outcome: CandidateOutcome
                              ) -> None:
        # FIXME add diff!
        diff = "FIXMEFIXMEFIXME"
        event = 'PATCH-ACCEPTED' if outcome.is_repair else 'PATCH-REJECTED'
        self._write((event, candidate.id, diff))
