# -*- coding: utf-8 -*-
from typing import List, Dict, Any, Type, Optional, Iterator
import glob
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
from bugzoo.core import FileLine, Patch
from bugzoo import Bug as Snapshot

from .core import Language, TestCoverageMap
from .coverage import coverage_for_config
from .test import BugZooTestSuite, TestSuite
from .candidate import Candidate
from .searcher import Searcher
from .program import Program
from .problem import Problem
from .config import Config, OptimizationsConfig
from .snippet import SnippetDatabase
from .exceptions import BadConfigurationException, LanguageNotSupported
from .localization import (Localization, ample, genprog, jaccard, ochiai,
                           tarantula)
from .events import (DarjeelingEventHandler, DarjeelingEventProducer,
                     EventEchoer, CsvEventLogger)
from .transformation import Transformation
from .transformation import find_all as find_all_transformations
from .transformation.classic import (DeleteStatement, ReplaceStatement,
                                     PrependStatement)

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)


@attr.s
class Session(DarjeelingEventProducer):
    """Used to manage and inspect an interactive repair session."""
    dir_patches = attr.ib(type=str)
    searcher = attr.ib(type=Searcher)
    _problem = attr.ib(type=Problem)
    terminate_early = attr.ib(type=bool, default=True)
    _patches = attr.ib(type=List[Candidate], factory=list)

    def __attrs_post_init__(self) -> None:
        DarjeelingEventProducer.__init__(self)

    @staticmethod
    def from_config(client_bugzoo: bugzoo.Client, cfg: Config) -> 'Session':
        """Creates a new repair session according to a given configuration."""
        # create the patch directory
        dir_patches = cfg.dir_patches
        if os.path.exists(dir_patches):
            logger.warning("clearing existing patch directory")
            for fn in glob.glob(f'{dir_patches}/*.diff'):
                if os.path.isfile(fn):
                    os.remove(fn)

        # seed the RNG
        # FIXME use separate RNG for each session
        random.seed(cfg.seed)

        logger.info("using %d threads", cfg.threads)
        logger.info("using language: %s", cfg.language.value)
        logger.info("using optimizations: %s", cfg.optimizations)
        logger.info("using coverage config: %s", cfg.coverage)
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

        # build program
        logger.debug("building program...")
        program = Program.from_config(client_bugzoo, cfg)
        logger.debug("built program: %s", program)

        # compute coverage
        logger.info("computing coverage information...")
        coverage = coverage_for_config(client_bugzoo, program, cfg.coverage)
        logger.info("computed coverage information")
        logger.debug("coverage: %s", coverage)

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
                                          program.snapshot,
                                          files)

        # build problem
        problem = Problem(bz=client_bugzoo,
                          language=cfg.language,
                          program=program,
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
        searcher = Searcher.from_config(cfg.search, problem, tx,
                                        threads=cfg.threads,
                                        candidate_limit=cfg.limit_candidates,
                                        time_limit=cfg.limit_time)

        # build session
        session = Session(dir_patches=dir_patches,
                          problem=problem,
                          searcher=searcher,
                          terminate_early=cfg.terminate_early)

        # attach listeners
        session.attach_handler(EventEchoer())
        csv_event_log_filename = os.path.join(os.getcwd(), 'events.csv')
        csv_event_logger = CsvEventLogger(csv_event_log_filename, problem)
        session.attach_handler(csv_event_logger)

        return session

    @property
    def snapshot(self) -> Snapshot:
        """The snapshot for the program being repaired."""
        return self.searcher.problem.bug

    @property
    def problem(self) -> Problem:
        """The repair problem that is being solved in this session."""
        return self.searcher.problem

    def attach_handler(self, handler: DarjeelingEventHandler) -> None:
        super().attach_handler(handler)
        self.searcher.attach_handler(handler)

    def remove_handler(self, handler: DarjeelingEventHandler) -> None:
        super().remove_handler(handler)
        self.searcher.remove_handler(handler)

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
    def has_found_patch(self) -> bool:
        """Returns :code:`True` if an acceptable patch has been found."""
        return len(self._patches) > 0

    @property
    def num_candidate_evaluations(self) -> int:
        return self.searcher.num_candidate_evals

    @property
    def running_time_secs(self) -> float:
        """Number of seconds that the search has been running."""
        return self.searcher.time_running.seconds

    @property
    def patches(self) -> Iterator[Patch]:
        """Returns an iterator over the patches found during this session."""
        for candidate in self._patches:
            yield candidate.to_diff(self._problem)

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

        self._save_patches_to_disk()

    def pause(self) -> None:
        """Pauses the session."""
        raise NotImplementedError

    def _save_patches_to_disk(self) -> None:
        logger.debug("saving patches to disk...")
        os.makedirs(self.dir_patches, exist_ok=True)
        for i, patch in enumerate(self._patches):
            diff = str(patch.to_diff(self.problem))
            fn_patch = os.path.join(self.dir_patches, '{}.diff'.format(i))
            logger.debug("writing patch to %s", fn_patch)
            try:
                with open(fn_patch, 'w') as f:
                    f.write(diff)
            except OSError:
                logger.exception("failed to write patch: %s", fn_patch)
                raise
            logger.debug("wrote patch to %s", fn_patch)
        logger.debug("saved patches to disk")

    def __enter__(self) -> 'Session':
        self.run()
        return self
