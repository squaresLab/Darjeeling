# -*- coding: utf-8 -*-
__all__ = ('EchoSearchEvents',)

from .search_listener import SearchListener
from ..core import Test, TestOutcome, BuildOutcome
from ..candidate import Candidate
from ..outcome import CandidateOutcome


class EchoSearchEvents(SearchListener):
    """Prints search events to the stdout.
    This class exists purely for testing and debugging purposes.
    """
    def on_test_finished(self,
                         candidate: Candidate,
                         test: Test,
                         outcome: TestOutcome
                         ) -> None:
        print(f"TEST FINISHED: {test.name}")

    def on_test_started(self, candidate: Candidate, test: Test) -> None:
        print(f"TEST STARTED: {test.name}")

    def on_build_started(self, candidate: Candidate) -> None:
        print(f"BUILD STARTED: {candidate}")

    def on_build_finished(self,
                          candidate: Candidate,
                          outcome: BuildOutcome
                          ) -> None:
        print(f"BUILD FINISHED: {candidate}")

    def on_candidate_started(self, candidate: Candidate) -> None:
        print(f"CANDIDATE STARTED: {candidate}")

    def on_candidate_finished(self,
                              candidate: Candidate,
                              outcome: CandidateOutcome
                              ) -> None:
        print(f"CANDIDATE FINISHED: {candidate}")
