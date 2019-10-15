# -*- coding: utf-8 -*-
__all__ = ('SimpleCSVSearchEventLogger',)

import csv
import os

import attr

from .observer import SearchObserver
from ..core import Test, TestOutcome, BuildOutcome
from ..candidate import Candidate
from ..outcome import CandidateOutcome


@attr.s
class SimpleCSVSearchEventLogger(SearchObserver):
    filename: str = attr.ib()

    @filename.validator
    def validate_filename(self, attr, value) -> None:
        if not os.path.isabs(self.filename):
            raise ValueError("'filename' must be an absolute path")

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

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
