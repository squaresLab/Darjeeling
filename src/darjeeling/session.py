# -*- coding: utf-8 -*-
__all__ = ('Session',)

from typing import Iterator, List
import glob
import os
import random

import attr
import kaskara
from bugzoo.core import Patch
from bugzoo import Bug as Snapshot
from loguru import logger

from .core import Language, TestCoverageMap
from .environment import Environment
from .candidate import Candidate
from .resources import ResourceUsageTracker
from .searcher import Searcher
from .problem import Problem
from .config import Config
from .snippet import (SnippetDatabase, StatementSnippetDatabase,
                      LineSnippetDatabase)
from .localization import Localization
from .events import DarjeelingEventHandler, DarjeelingEventProducer


@attr.s
class Session(DarjeelingEventProducer):
    """Used to manage and inspect an interactive repair session."""
    dir_patches: str = attr.ib()
    searcher: Searcher = attr.ib()
    resources: ResourceUsageTracker = attr.ib()
    _problem: Problem = attr.ib()
    terminate_early: bool = attr.ib(default=True)
    _patches: List[Candidate] = attr.ib(factory=list)

    def __attrs_post_init__(self) -> None:
        DarjeelingEventProducer.__init__(self)

    @staticmethod
    def from_config(environment: Environment, cfg: Config) -> 'Session':
        """Creates a new repair session according to a given configuration."""
        logger.debug('preparing patch directory')
        dir_patches = cfg.dir_patches
        if os.path.exists(dir_patches):
            logger.warning("clearing existing patch directory")
            for fn in glob.glob(f'{dir_patches}/*.diff'):
                if os.path.isfile(fn):
                    os.remove(fn)
        logger.debug('prepared patch directory')

        # ensure that Kaskara is installed
        logger.info('ensuring that kaskara installation is complete '
                    '(this may take 20 minutes if Kaskara is not up-to-date)')
        kaskara.post_install()
        logger.info('ensured that kaskara installation is complete')

        # seed the RNG
        # FIXME use separate RNG for each session
        random.seed(cfg.seed)

        logger.info(f"using {cfg.threads} threads")
        logger.info(f"using language: {cfg.program.language.value}")
        logger.info(f"using optimizations: {cfg.optimizations}")
        logger.info(f"using coverage config: {cfg.coverage}")
        logger.info(f"running redundant tests? {cfg.run_redundant_tests}")
        logger.info(f"using random number generator seed: {cfg.seed}")

        if not cfg.terminate_early:
            logger.info("search will continue after an acceptable patch has been discovered")
        else:
            logger.info("search will terminate when an acceptable patch has been discovered")

        # create the resource tracker
        resources = ResourceUsageTracker.with_limits(cfg.resource_limits)
        logger.info(str(cfg.resource_limits))

        # build program
        logger.debug("building program...")
        program = cfg.program.build(environment)
        logger.debug(f"built program: {program}")

        # compute coverage
        logger.info("computing coverage information...")
        coverage = cfg.coverage.build(environment, program)
        logger.info("computed coverage information")
        logger.debug(f"coverage: {coverage}")

        # compute localization
        logger.info("computing fault localization...")
        localization = \
            Localization.from_config(coverage, cfg.localization)
        logger.info(f"computed fault localization:\n{localization}")

        # determine implicated files
        files = localization.files

        if program.language in (Language.CPP, Language.C):
            kaskara_project = kaskara.Project(dockerblade=environment.dockerblade,
                                              image=program.image,
                                              directory=program.source_directory,
                                              files=files)
            analyser = kaskara.clang.ClangAnalyser()
            analysis = analyser.analyse(kaskara_project)
        elif program.language == Language.PYTHON:
            kaskara_project = kaskara.Project(dockerblade=environment.dockerblade,
                                              image=program.image,
                                              directory=program.source_directory,
                                              files=files)
            analyser = kaskara.python.PythonAnalyser()
            analysis = analyser.analyse(kaskara_project)
        else:
            analysis = None

        # build problem
        problem = Problem.build(environment=environment,
                                config=cfg,
                                language=program.language,
                                program=program,
                                coverage=coverage,
                                analysis=analysis,
                                localization=localization)

        logger.info("constructing database of donor snippets...")
        snippets: SnippetDatabase
        if analysis is not None:
            snippets = StatementSnippetDatabase.from_kaskara(analysis, cfg)
        else:
            snippets = LineSnippetDatabase.for_problem(problem)
        logger.info(f"constructed database of donor snippets: {len(snippets)} snippets")

        transformations = cfg.transformations.build(problem, snippets)
        searcher = cfg.search.build(problem,
                                    resources=resources,
                                    transformations=transformations,
                                    threads=cfg.threads,
                                    run_redundant_tests=cfg.run_redundant_tests)

        # build session
        return Session(dir_patches=dir_patches,
                       resources=resources,
                       problem=problem,
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

    @property
    def coverage(self) -> TestCoverageMap:
        """The test suite coverage for the program under repair."""
        return self.problem.coverage

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
    def patches(self) -> Iterator[Patch]:
        """Returns an iterator over the patches found during this session."""
        for candidate in self._patches:
            yield candidate.to_diff()

    def close(self) -> None:
        """Closes the session."""
        # wait for threads to finish gracefully before exiting
        self.searcher.close()

        time_running_mins = self.resources.wall_clock.duration / 60
        logger.info(f"found {len(self._patches)} plausible patches")
        logger.info(f"time taken: {time_running_mins:.2f} minutes")
        logger.info(f"# test evaluations: {self.resources.tests}")
        logger.info(f"# candidate evaluations: {self.resources.candidates}")

        self._save_patches_to_disk()

    def pause(self) -> None:
        """Pauses the session."""
        raise NotImplementedError

    def _save_patches_to_disk(self) -> None:
        logger.debug("saving patches to disk...")
        os.makedirs(self.dir_patches, exist_ok=True)
        for i, patch in enumerate(self._patches):
            diff = str(patch.to_diff())
            fn_patch = os.path.join(self.dir_patches, f'{i}.diff')
            logger.debug(f"writing patch to {fn_patch}")
            try:
                with open(fn_patch, 'w') as f:
                    f.write(diff)
            except OSError:
                logger.exception(f"failed to write patch: {fn_patch}")
                raise
            logger.debug(f"wrote patch to {fn_patch}")
        logger.debug("saved patches to disk")

    def __enter__(self) -> 'Session':
        self.run()
        return self
