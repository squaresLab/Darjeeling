# -*- coding: utf-8 -*-
__all__ = ('SearchObserver',)

import abc

from ..core import Test, TestOutcome, BuildOutcome
from ..candidate import Candidate


class SearchObserver(abc.ABC):
    @abc.abstractmethod
    def on_test_finished(self, test: Test, outcome: TestOutcome) -> None:
        ...

    @abc.abstractmethod
    def on_test_started(self, test: Test) -> None:
        ...

    @abc.abstractmethod
    def on_build_started(self, candidate: Candidate) -> None:
        ...

    @abc.abstractmethod
    def on_build_finished(self,
                          candidate: Candidate,
                          outcome: BuildOutcome
                          ) -> None:
        ...
