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

from .core import Language
from .test import BugZooTestSuite
from .candidate import Candidate
from .searcher import Searcher
from .problem import Problem
from .settings import Settings
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
    def from_yml(client_bugzoo: bugzoo.Client,
                 yml: Dict[str, Any],
                 *,
                 terminate_early: bool = True,
                 seed: Optional[int] = None,
                 threads: Optional[int] = None,
                 limit_candidates: Optional[int] = None,
                 limit_time_minutes: Optional[int] = None
                 ) -> 'Session':
        """Creates a new repair session according to a given configuration.

        Parameters
        ----------
        yml: Dict[str, Any]
            A dictionary representation of the YAML configuration.
        seed: Optional[int] = None
            An optional seed for the random number generator.
        terminate_early: bool = True
            Specifies whether or not the search should terminate upon
            discovering an acceptable patch.
        limit_candidates: Optional[int] = None
            An optional limit on the number of candidate patches that may be
            considered by the search.
        limit_time_minutes: Optional[int] = None
            An optional limit on the number of minutes that may be spent
            searching for an acceptable patch.
        """
        # are any resource limits specified?
        has_limits = 'resource-limits' in yml

        # create the patch directory
        dir_patches = os.path.abspath('patches')
        if os.path.exists(dir_patches):
            logger.warning("destroying existing patch directory")
            shutil.rmtree(dir_patches)

        # fetch the bugzoo snapshot name
        if 'snapshot' not in yml:
            raise BadConfigurationException("'snapshot' property is missing")
        if not isinstance(yml['snapshot'], str):
            m = "'snapshot' property should be a string"
            raise BadConfigurationException(m)
        name_snapshot = yml['snapshot']

        # should we continue to search for repairs?
        if not terminate_early:
            logger.info("search will continue after an acceptable patch has been discovered")
        else:
            logger.info("search will terminate when an acceptable patch has been discovered")

        # how many threads should we use?
        if threads is not None:
            logger.info("using threads override: %d threads", threads)
        elif 'threads' in yml:
            if not isinstance(yml['threads'], int):
                m = "'threads' property should be an int"
                raise BadConfigurationException(m)
            threads = yml['threads']
            logger.info("using threads specified by configuration: %d threads",
                        threads)
        else:
            threads = 1
            logger.info("using default number of threads: %d", threads)
        if threads < 1:
            m = "number of threads must be greater than or equal to 1."
            raise BadConfigurationException(m)

        # determine the limit on the number of candidate repairs
        if limit_candidates is not None:
            logger.info("using candidate limit override: %d candidates",
                        limit_candidates)
        elif has_limits and 'candidates' in yml['resource-limits']:
            if not isinstance(yml['resource-limits']['candidates'], int):
                m = "'candidates' property in 'resource-limits' section should be an int"
                raise BadConfigurationException(m)
            limit_candidates = yml['resource-limits']['candidates']
            logger.info("using candidate limit specified by configuration: %d candidates",  # noqa: pycodestyle
                        limit_candidates)
        else:
            logger.info("no limit on number of candidate evaluations")

        # determine time limit
        if limit_time_minutes is not None:
            logger.info("using time limit override: %d minutes",
                        limit_time_minutes)
        elif has_limits and 'time-minutes' in yml['resource-limits']:
            if not isinstance(yml['resource-limits']['time-minutes'], int):
                m = "'time-minutes' property in 'resource-limits' section should be an int"  # noqa: pycodestyle
                raise BadConfigurationException(m)
            limit_time_minutes = yml['resource-limits']['time-minutes']
            logger.info("using time limit specified by configuration: %d minutes",  # noqa: pycodestyle
                        limit_time_minutes)
        else:
            logger.info("no time limit is being enforced")

        # ensure time limit is legal
        limit_time = None  # type: Optional[timedelta]
        if limit_time_minutes:
            if limit_time_minutes < 1:
                m = "time limit must be greater than or equal to 1 minute"
                raise BadConfigurationException(m)
            limit_time = timedelta(minutes=limit_time_minutes)

        # check if search is unbounded
        if not limit_time and not limit_candidates:
            m = "no resource limits were specified; resource use will be unbounded"  # noqa: pycodestyle
            logger.warn(m)

        # seed override
        if seed is not None:
            logger.info("using random number generator seed override: %d",
                        seed)

        # no seed override; seed provided in config
        elif 'seed' in yml:
            if not isinstance(yml['seed'], int):
                m = "'seed' property should be an int."
                raise BadConfigurationException(m)
            elif yml['seed'] < 0:
                m = "'seed' property should be greater than or equal to zero."
                raise BadConfigurationException(m)
            seed = yml['seed']
            logger.info("using random number generator seed provided by configuration: %d",  # noqa: pycodestyle
                        seed)

        # no seed override or provided in provided; use current date/time
        elif seed is None:
            random.seed(datetime.now())
            seed = random.randint(0, sys.maxsize)
            logger.info("using random number generator seed based on current date and time: %d",  # noqa: pycodestyle
                        seed)

        # seed the RNG
        # FIXME use separate RNG for each session
        random.seed(seed)

        # determine the language
        if 'language' not in yml:
            m = "'language' property is missing"
            raise BadConfigurationException(m)
        if not isinstance(yml['language'], str):
            m = "'language' property should be a string"
            raise BadConfigurationException(m)
        try:
            language = Language.find(yml['language'])
        except LanguageNotSupported:
            supported = ', '.join([l.value for l in Language])
            supported = "(supported languages: {})".format(supported)
            m = "unsupported language [{}]. {}"
            m = m.format(yml['language'], supported)
            raise BadConfigurationException(m)
        logger.info("using language: %s", language.value)

        # build the settings
        opts = yml.get('optimizations', {})
        settings = \
            Settings(use_scope_checking=opts.get('use-scope-checking', True),
                     use_syntax_scope_checking=opts.get('use-syntax-scope-checking', True),
                     ignore_dead_code=opts.get('ignore-dead-code', True),
                     ignore_equivalent_appends=opts.get('ignore-equivalent-prepends', True),
                     ignore_untyped_returns=opts.get('ignore-untyped-returns', True),
                     ignore_string_equivalent_snippets=opts.get('ignore-string-equivalent-snippets', True),
                     ignore_decls=opts.get('ignore-decls', True),
                     only_insert_executed_code=opts.get('only-insert-executed-code', True))
        logger.info("using repair settings: %s", settings)

        # fetch the transformation schemas
        if 'transformations' not in yml:
            m = "'transformations' section is missing"
            raise BadConfigurationException(m)
        if not isinstance(yml['transformations'], dict):
            m = "'transformations' section should be an object"
            raise BadConfigurationException(m)
        if not 'schemas' in yml['transformations']:
            m = "'schemas' property missing in 'transformations' section"
            raise BadConfigurationException(m)
        if not isinstance(yml['transformations']['schemas'], list):
            m = "'schemas' property should be a list"
            raise BadConfigurationException(m)

        def schema_from_dict(d: Dict[str, Any]) -> Type[Transformation]:
            if not isinstance(d, dict):
                m = "expected an object but was a {}".format(type(d).__name__)
                m = "illegal schema description: {}".format(m)
                raise BadConfigurationException(m)
            if not 'type' in d:
                m = "missing 'type' property in schema description"
                raise BadConfigurationException(m)

            name_schema = d['type']
            try:
                return Transformation.find_schema(name_schema)
            except KeyError:
                known_schemas = "(known schemas: {})".format(
                    ', '.join(Transformation.schemas()))
                m = "no schema with name [{}]. {}"
                m = m.format(name_schema, known_schemas)
                raise BadConfigurationException(m)

        schemas = \
            [schema_from_dict(d) for d in yml['transformations']['schemas']]

        # fetch the BugZoo snapshot and ensure that it's installed
        if not name_snapshot in client_bugzoo.bugs:
            m = "snapshot not found: {}".format(name_snapshot)
            raise BadConfigurationException(m)

        snapshot = client_bugzoo.bugs[name_snapshot]

        if not client_bugzoo.bugs.is_installed(snapshot):
            m = "snapshot not installed: {}".format(name_snapshot)
            raise BadConfigurationException(m)

        # compute coverage
        logger.info("computing coverage information...")
        coverage = client_bugzoo.bugs.coverage(snapshot)
        logger.info("computed coverage information")

        # compute localization
        logger.info("computing fault localization...")
        if 'localization' not in yml:
            m = "'localization' section is missing"
            raise BadConfigurationException(m)

        localization = \
            Localization.from_config(coverage, yml['localization'])
        logger.info("computed fault localization:\n%s", localization)

        # determine implicated files and lines
        files = localization.files
        lines = list(localization)  # type: List[FileLine]

        # compute analysis
        analysis = kaskara.Analysis.build(client_bugzoo,
                                          snapshot,
                                          files)

        # build test suite
        test_suite = BugZooTestSuite.from_bug(client_bugzoo, snapshot)

        # build problem
        problem = Problem(bz=client_bugzoo,
                          bug=snapshot,
                          language=language,
                          test_suite=test_suite,
                          coverage=coverage,
                          analysis=analysis,
                          settings=settings)

        # build snippet database
        logger.info("constructing database of donor snippets...")
        snippets = SnippetDatabase.from_statements(
            analysis.statements,
            use_canonical_form=settings.ignore_string_equivalent_snippets)
        logger.info("constructed database of donor snippets: %d snippets",
                    len(snippets))

        # FIXME build and index transformations
        # FIXME does not allow lazy construction!
        logger.info("constructing transformation database...")
        tx = list(find_all_transformations(problem, lines, snippets, schemas))
        logger.info("constructed transformation database: %d transformations",  # noqa: pycodestyle
                    len(tx))

        # build the search strategy
        searcher = Searcher.from_dict(yml['algorithm'], problem, tx,
                                      threads=threads,
                                      candidate_limit=limit_candidates,
                                      time_limit=limit_time)

        # build session
        return Session(dir_patches=dir_patches,
                       searcher=searcher,
                       terminate_early=terminate_early)

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
