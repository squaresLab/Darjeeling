# -*- coding: utf-8 -*-
__all__ = ('SearchObserver',)

import abc

from ..core import Test, TestOutcome


class SearchObserver(abc.ABC):
    @abc.abstractmethod
    def on_test_finished(self, test: Test, outcome: TestOutcome) -> None:
        ...

    @abc.abstractmethod
    def on_test_started(self, test: Test) -> None:
        ...
