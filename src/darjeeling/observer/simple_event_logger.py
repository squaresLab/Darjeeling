# -*- coding: utf-8 -*-
__all__ = ('SimpleEventLogger',)

from typing import Tuple, Optional
import csv
import functools
import io
import os

import attr

from .observer import SearchObserver
from ..core import Test, TestOutcome, BuildOutcome
from ..candidate import Candidate
from ..outcome import CandidateOutcome


@attr.s(eq=False, hash=False)
class SimpleEventLogger(SearchObserver):
    """Logs search events to a CSV file.

    Attributes
    ----------
    filename: str
        The absolute path to the file to which events should be logged.
    """
    filename: str = attr.ib()
    _file: Optional[io.StringIO] = \
        attr.ib(default=None, init=False, repr=False)
    _writer: Optional[csv._writer] = \
        attr.ib(default=None, init=False, repr=False)

    @filename.validator
    def validate_filename(self, attr, value) -> None:
        if not os.path.isabs(self.filename):
            raise ValueError("'filename' must be an absolute path")

    def open(self) -> None:
        self._file = open(self.filename, 'w')
        self._writer = csv.writer(self._file)

    def close(self) -> None:
        if self._file:
            self._file.close()
            self._writer = None
            self._file = None

    def _must_be_open(self, method):
        @functools.wraps(method)
        def wrapped(*args, **kwargs):
            if not self._writer:
                m = (f"{self.__class__.__name__} instance must be open"
                     f" before calling {method.__name__}")
                raise RuntimeError(m)
            return method(*args, **kwargs)

        return wrapped

    @_must_be_open
    def on_test_finished(self,
                         candidate: Candidate,
                         test: Test,
                         outcome: TestOutcome
                         ) -> None:
        status = 'passed' if outcome.successful else 'failed'
        duration = f'{outcome.time_taken:.3f}'
        row: Tuple[str, ...] = \
            ('TEST-OUTCOME', candidate.id, test.name, status, duration)
        self._writer.writerow(row)

    @_must_be_open
    def on_test_started(self, candidate: Candidate, test: Test) -> None:
        self._writer.writerow(('TEST-STARTED', candidate.id, test.name))

    @_must_be_open
    def on_build_started(self, candidate: Candidate) -> None:
        self._writer.writerow(('BUILD-STARTED', candidate.id))

    @_must_be_open
    def on_build_finished(self,
                          candidate: Candidate,
                          outcome: BuildOutcome
                          ) -> None:
        status = 'passed' if outcome.successful else 'failed'
        duration = f'{test.time_taken:.3f}'
        row: Tuple[str, ...] = \
            ('BUILD-OUTCOME', candidate.id, status, duration)
        self._writer.writerow(row)

    @_must_be_open
    def on_candidate_started(self, candidate: Candidate) -> None:
        # FIXME add diff!
        diff = "FIXMEFIXMEFIXME"
        self._writer.writerow(('CANDIDATE-STARTED', candidate.id, diff))

    @_must_be_open
    def on_candidate_finished(self,
                              candidate: Candidate,
                              outcome: CandidateOutcome
                              ) -> None:
        # FIXME add diff!
        diff = "FIXMEFIXMEFIXME"
        event = 'PATCH-ACCEPTED' if outcome.successful else 'PATCH-REJECTED'
        self._writer.writerow((event, candidate.id, diff))
