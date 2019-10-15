# -*- coding: utf-8 -*-
__all__ = ('SimpleCSVSearchEventLogger',)

import csv
import os

import attr

from .observer import SearchObserver
from ..core import Test, TestOutcome, BuildOutcome
from ..candidate import Candidate
from ..outcome import CandidateOutcome


@attr.s(eq=False, hash=False)
class SimpleCSVSearchEventLogger(SearchObserver):
    filename: str = attr.ib()
    _file: Optional[io.StringIO] = \
        attr.ib(default=None, init=None, repr=False)

    @filename.validator
    def validate_filename(self, attr, value) -> None:
        if not os.path.isabs(self.filename):
            raise ValueError("'filename' must be an absolute path")

    def open(self) -> None:
        """Opens the associated CSV file handle."""
        self._file = open(self.filename, 'w')

    def close(self) -> None:
        """Closes the associated CSV file handle."""
        if self._file:
            self._file.close()
            self._file = None

    def on_test_finished(self,
                         candidate: Candidate,
                         test: Test,
                         outcome: TestOutcome
                         ) -> None:
        ...

    def on_test_started(self, candidate: Candidate, test: Test) -> None:
        ...

    def on_build_started(self, candidate: Candidate) -> None:
        ...

    def on_build_finished(self,
                          candidate: Candidate,
                          outcome: BuildOutcome
                          ) -> None:
        ...

    def on_candidate_started(self, candidate: Candidate) -> None:
        ...

    def on_candidate_finished(self,
                              candidate: Candidate,
                              outcome: CandidateOutcome
                              ) -> None:
        ...
