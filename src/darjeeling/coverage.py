# -*- coding: utf-8 -*-
__all__ = ('coverage_for_snapshot',)

from bugzoo import Client as BugZooClient, Bug as Snapshot

from .core import TestCoverageMap, TestSuite, Test


def coverage_for_snapshot(bz: BugZooClient,
                          snapshot: Snapshot,
                          tests: TestSuite
                          ) -> TestCoverageMap:
    raise NotImplementedError
