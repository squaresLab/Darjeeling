from typing import List, Optional, Dict, Any, Type
import logging
from datetime import datetime, timedelta
import sys
import random
import warnings
import shutil
import os

import bugzoo
import cement
import yaml
import kaskara
from bugzoo.core import FileLine

from ..core import Language
from ..candidate import all_single_edit_patches
from ..candidate import Candidate
from ..transformation import Transformation
from ..transformation import find_all as find_all_transformations
from ..transformation.classic import DeleteStatement, \
                                     ReplaceStatement, \
                                     PrependStatement
from ..exceptions import BadConfigurationException, LanguageNotSupported
from ..searcher import Searcher
from ..problem import Problem
from ..localization import Localization, \
                           ample, \
                           genprog, \
                           jaccard, \
                           ochiai, \
                           tarantula
from ..snippet import SnippetDatabase
from ..settings import Settings
from .. import localization

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)

BANNER = 'DARJEELING'


class BaseController(cement.Controller):
    class Meta:
        label = 'base'
        description = 'Language-independent automated program repair'
        arguments = [
            (['--version'], {'action': 'version', 'version': BANNER}),
        ]

    def default(self):
        # type: () -> None
        self.app.args.print_help()

    @cement.ex(
        help='attempt to automatically repair a given program',
        arguments=[
            (['filename'],
             {'help': ('a Darjeeling configuration file describing the faulty '
                       'program and how it should be repaired.') }),
            (['--seed'],
             {'help': 'random number generator seed',
              'type': int}),
            (['--max-candidates'],
             {'dest': 'limit_candidates',
              'type': int,
              'help': ('the maximum number of candidate patches that may be '
                       'considered by the search.')}),
            (['--max-time-mins'],
             {'dest': 'limit_time_minutes',
              'type': int,
              'help': ('the maximum number of minutes that may be spent '
                       'searching for a patch.')}),
            (['--continue'],
             {'dest': 'terminate_early',
              'action': 'store_false',
              'help': ('continue to search for patches after an acceptable '
                       ' patch has been discovered.')}),
            (['--threads'],
             {'dest': 'threads',
              'type': int,
              'help': ('number of threads over which the repair workload '
                       'should be distributed')})
        ]
    )
    def repair(self) -> None:
        filename = self.app.pargs.filename  # type: str
        seed = self.app.pargs.seed  # type: Optional[int]
        terminate_early = self.app.pargs.terminate_early  # type: bool
        threads = self.app.pargs.threads  # type: Optional[int]
        limit_candidates = \
            self.app.pargs.limit_candidates  # type: Optional[int]
        limit_time_minutes = \
            self.app.pargs.limit_time_minutes  # type: Optional[int]

        dir_patches = 'patches'
        if os.path.exists(dir_patches):
            logger.warning("destroying existing patch directory")
            shutil.rmtree(dir_patches)

        with open(filename, 'r') as f:
            yml = yaml.load(f)

        has_limits = 'resource-limits' in yml

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

        limit_time = None  # type: Optional[timedelta]
        if limit_time_minutes:
            if limit_time_minutes < 1:
                m = "time limit must be greater than or equal to 1 minute"
                raise BadConfigurationException(m)
            limit_time = timedelta(minutes=limit_time_minutes)

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

        # no seed override or provided in provided
        # use current date/time
        elif seed is None:
            random.seed(datetime.now())
            seed = random.randint(0, sys.maxsize)
            logger.info("using random number generator seed based on current date and time: %d",  # noqa: pycodestyle
                        seed)

        # seed the RNG
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

        # fetch the bugzoo snapshot
        if 'snapshot' not in yml:
            raise BadConfigurationException("'snapshot' property is missing")
        if not isinstance(yml['snapshot'], str):
            m = "'snapshot' property should be a string"
            raise BadConfigurationException(m)
        name_snapshot = yml['snapshot']

        # connect to BugZoo
        logger.info("connecting to BugZoo server")
        with bugzoo.server.ephemeral(timeout_connection=120) as client_bugzoo:
            logger.info("connected to BugZoo server")
            try:
                snapshot = client_bugzoo.bugs[name_snapshot]
            except bugzoo.exceptions.BugZooException:
                logger.error("failed to fetch BugZoo snapshot: %s",
                             name_snapshot)
                sys.exit(1)

            if not client_bugzoo.bugs.is_installed(snapshot):
                logger.error("BugZoo snapshot is not installed: %s",
                             name_snapshot)
                sys.exit(1)

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

            # build problem
            problem = Problem(bz=client_bugzoo,
                              bug=snapshot,
                              language=language,
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
            logger.info("constructing transformation database...")
            tx = list(find_all_transformations(problem, lines, snippets, schemas))
            logger.info("constructed transformation database: %d transformations",  # noqa: pycodestyle
                        len(tx))

            # build the search strategy
            # FIXME pass limits!
            searcher = Searcher.from_dict(yml['algorithm'], problem, tx,
                                          threads=threads,
                                          candidate_limit=limit_candidates,
                                          time_limit=limit_time)

            logger.info("beginning search process...")
            patches = []  # type: List[Candidate]
            if terminate_early:
                try:
                    patches.append(next(searcher.__iter__()))
                except StopIteration:
                    pass
            else:
                patches = list(searcher)
            if not patches:
                logger.info("failed to find a patch")

            # wait for threads to finish gracefully before exiting
            searcher.close()

            # report stats
            num_test_evals = searcher.num_test_evals
            num_candidate_evals = searcher.num_candidate_evals
            time_running_mins = searcher.time_running.seconds / 60

            logger.info("found %d plausible patches", len(patches))
            logger.info("time taken: %.2f minutes", time_running_mins)
            logger.info("# test evaluations: %d", searcher.num_test_evals)
            logger.info("# candidate evaluations: %d", searcher.num_candidate_evals)

            # save patches to disk
            os.makedirs(dir_patches, exist_ok=True)
            for i, patch in enumerate(patches):
                diff = str(patch.to_diff(problem))
                fn_patch = os.path.join(dir_patches, '{}.diff'.format(i))
                logger.debug("writing patch to %s", fn_patch)
                try:
                    with open(fn_patch, 'w') as f:
                        f.write(diff)
                except Exception:
                    logger.exception("failed to write patch: %s", fn_patch)
                    raise
                logger.debug("wrote patch to %s", fn_patch)


class CLI(cement.App):
    class Meta:
        label = 'darjeeling'
        handlers = [BaseController]


def main():
    log_to_stdout = logging.StreamHandler()
    log_to_stdout.setLevel(logging.INFO)
    # logger.addHandler(log_to_stdout)
    logging.getLogger('darjeeling').addHandler(log_to_stdout)

    with CLI() as app:
        app.run()
