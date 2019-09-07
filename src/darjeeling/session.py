# -*- coding: utf-8 -*-
from typing import List, Dict, Any, Type, Optional
import os
import sys
import asyncio
import shutil
import logging
import random
import asyncio
from datetime import timedelta, datetime

import attr
import bugzoo
import kaskara
from bugzoo.core import FileLine
from bugzoo import Bug as Snapshot

from .core import Language, TestCoverageMap
from .test import BugZooTestSuite
from .candidate import Candidate
from .searcher import Searcher
from .problem import Problem
from .config import Config, OptimizationsConfig
from .snippet import SnippetDatabase
from .exceptions import BadConfigurationException, LanguageNotSupported
from .localization import (Localization, ample, genprog, jaccard, ochiai,
                           tarantula)
from .transformation import Transformation
from .transformation import find_all as find_all_transformations
from .transformation.classic import (DeleteStatement, ReplaceStatement,
                                     PrependStatement)

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)


@attr.s
class Session:
    """Used to manage and inspect an interactive repair session."""
    dir_patches = attr.ib(type=str)
    searcher = attr.ib(type=Searcher)
    terminate_early = attr.ib(type=bool, default=True)
    _patches = attr.ib(type=List[Candidate], factory=list)

    @staticmethod
    def from_config(client_bugzoo: bugzoo.Client, cfg: Config) -> 'Session':
        """Creates a new repair session according to a given configuration."""
        # create the patch directory
        dir_patches = os.path.abspath('patches')
        if os.path.exists(dir_patches):
            logger.warning("destroying existing patch directory")
            shutil.rmtree(dir_patches)

        # seed the RNG
        # FIXME use separate RNG for each session
        random.seed(cfg.seed)

        logger.info("using %d threads", cfg.threads)
        logger.info("using language: %s", cfg.language.value)
        logger.info("using optimizations: %s", cfg.optimizations)
        logger.info("using random number generator seed: %d", cfg.seed)

        if not cfg.terminate_early:
            logger.info("search will continue after an acceptable patch has been discovered")
        else:
            logger.info("search will terminate when an acceptable patch has been discovered")

        if cfg.limit_time_minutes is None:
            logger.info("no time limit is being enforced")
        if cfg.limit_time_minutes is not None:
            logger.info("using time limit: %d minutes", cfg.limit_time_minutes)

        if cfg.limit_candidates is not None:
            logger.info("using candidate limit: %d candidates", cfg.limit_candidates)  # noqa: pycodestyle
        else:
            logger.info("no limit on number of candidate evaluations")

        # check if search is unbounded
        if not cfg.limit_time and not cfg.limit_candidates:
            m = "no resource limits were specified; resource use will be unbounded"  # noqa: pycodestyle
            logger.warn(m)

        # fetch the BugZoo snapshot and ensure that it's installed
        if not cfg.snapshot in client_bugzoo.bugs:
            m = "snapshot not found: {}".format(cfg.snapshot)
            raise BadConfigurationException(m)

        snapshot = client_bugzoo.bugs[cfg.snapshot]

        if not client_bugzoo.bugs.is_installed(snapshot):
            m = "snapshot not installed: {}".format(snapshot)
            raise BadConfigurationException(m)

        # build test suite
        test_suite = BugZooTestSuite.from_bug(client_bugzoo, snapshot)

        # FIXME create from scratch!
        # compute coverage
        logger.info("computing coverage information...")
        coverage = TestCoverageMap.from_bugzoo(client_bugzoo.bugs.coverage(snapshot))  # noqa: pycodestyle
        logger.info("computed coverage information")

        # compute localization
        logger.info("computing fault localization...")
        localization = \
            Localization.from_config(coverage, cfg.localization)
        logger.info("computed fault localization:\n%s", localization)

        # determine implicated files and lines
        files = localization.files
        lines = list(localization)  # type: List[FileLine]

        # compute analysis
        analysis = kaskara.Analysis.build(client_bugzoo,
                                          snapshot,
                                          files)

        # build problem
        problem = Problem(bz=client_bugzoo,
                          bug=snapshot,
                          language=cfg.language,
                          test_suite=test_suite,
                          coverage=coverage,
                          analysis=analysis,
                          settings=cfg.optimizations)

        # build snippet database
        logger.info("constructing database of donor snippets...")
        snippets = SnippetDatabase.from_statements(
            analysis.statements,
            use_canonical_form=cfg.optimizations.ignore_string_equivalent_snippets)
        logger.info("constructed database of donor snippets: %d snippets",
                    len(snippets))

        # FIXME build and index transformations
        # FIXME does not allow lazy construction!
        schemas = [Transformation.find_schema(s.name) for s in cfg.transformations.schemas]
        logger.info("constructing transformation database...")
        tx = list(find_all_transformations(problem, lines, snippets, schemas))
        logger.info("constructed transformation database: %d transformations",  # noqa: pycodestyle
                    len(tx))

        # build the search strategy
        searcher = Searcher.from_dict(cfg.yml_search, problem, tx,
                                      threads=cfg.threads,
                                      candidate_limit=cfg.limit_candidates,
                                      time_limit=cfg.limit_time)

        # build session
        return Session(dir_patches=dir_patches,
                       searcher=searcher,
                       terminate_early=cfg.terminate_early)

    @property
    def snapshot(self) -> Snapshot:
        """The snapshot for the program being repaired."""
        return self.searcher.problem.bug

    @property
    def problem(self) -> Problem:
        """The repair problem that is being solved in this session."""
        return self.searcher.problem

    def run(self) -> None:
        logger.info("beginning search process...")
        if self.terminate_early:
            try:
                self._patches.append(next(self.searcher.__iter__()))
            except StopIteration:
                pass
        else:
            self._patches = list(self.searcher)
        if not self._patches:
            logger.info("failed to find a patch")

    @property
    def num_candidate_evaluations(self) -> int:
        return self.searcher.num_candidate_evals

    @property
    def running_time_secs(self) -> float:
        """Number of seconds that the search has been running."""
        return self.searcher.time_running.seconds

    def close(self) -> None:
        """Closes the session."""
        # wait for threads to finish gracefully before exiting
        self.searcher.close()

        # report stats
        num_test_evals = self.searcher.num_test_evals
        num_candidate_evals = self.searcher.num_candidate_evals
        time_running_mins = self.searcher.time_running.seconds / 60

        logger.info("found %d plausible patches", len(self._patches))
        logger.info("time taken: %.2f minutes", time_running_mins)
        logger.info("# test evaluations: %d", self.searcher.num_test_evals)
        logger.info("# candidate evaluations: %d",
                    self.searcher.num_candidate_evals)

    def pause(self) -> None:
        """Pauses the session."""
        raise NotImplementedError

    def _save_patches_to_disk(self) -> None:
        os.makedirs(self.dir_patches, exist_ok=True)
        for i, patch in enumerate(self._patches):
            diff = str(patch.to_diff(self.problem))
            fn_patch = os.path.join(self.dir_patches, '{}.diff'.format(i))
            logger.debug("writing patch to %s", fn_patch)
            try:
                with open(fn_patch, 'w') as f:
                    f.write(diff)
            except Exception:
                logger.exception("failed to write patch: %s", fn_patch)
                raise
            logger.debug("wrote patch to %s", fn_patch)

    def __enter__(self) -> 'Session':
        self.run()
        return self
