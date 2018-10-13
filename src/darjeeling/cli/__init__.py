from typing import List, Optional
import logging
from datetime import datetime
import sys
import random

import bugzoo
import cement
import yaml
import kaskara
from bugzoo.core import FileLine

from ..candidate import all_single_edit_patches
from ..candidate import Candidate
from ..transformation import find_all as find_all_transformations
from ..transformation.classic import DeleteStatement, \
                                     ReplaceStatement, \
                                     PrependStatement
from ..exceptions import BadConfigurationException
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

        with open(filename, 'r') as f:
            yml = yaml.load(f)

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
        elif 'limits' in yml and 'candidates' in yml['limits']:
            if not isinstance(yml['limits']['candidates'], int):
                m = "'candidates' property in 'limits' section should be an int"
                raise BadConfigurationException(m)
            limit_candidates = yml['limits']['candidates']
            logger.info("using candidate limit specified by configuration: %d candidates",  # noqa: pycodestyle
                        limit_candidates)

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

        # fetch the suspiciousness metric
        if 'localization' not in yml:
            m = "'localization' section is missing"
            raise BadConfigurationException(m)
        if not isinstance(yml['localization'], dict):
            m = "'localization' should be an object"
            raise BadConfigurationException(m)
        if not 'metric' in yml['localization']:
            m = "'metric' property is missing from 'localization' section"
            raise BadConfigurationException(m)
        if not isinstance(yml['localization']['metric'], str):
            m = "'metric' property in 'localization' should be a string"
            raise BadConfigurationException(m)
        name_metric = yml['localization']['metric']
        try:
            supported_metrics = {
                'genprog': genprog,
                'tarantula': tarantula,
                'ochiai': ochiai,
                'jaccard': jaccard,
                'ample': ample
            }
            logger.info("supported suspiciousness metrics: %s",
                        ', '.join(supported_metrics.keys()))
            metric = supported_metrics[name_metric]
        except KeyError:
            m = "suspiciousness metric not supported: {}".format(name_metric)
            raise BadConfigurationException(m)
        logger.info("using suspiciousness metric: %s", name_metric)

        # fetch the transformation schemas
        if 'transformations' not in yml:
            m = "'transformations' property is missing"
            raise BadConfigurationException(m)
        if not isinstance(yml['transformations'], list):
            m = "'transformations' property should be a list"
            raise BadConfigurationException(m)
        # FIXME
        schemas = [DeleteStatement, ReplaceStatement, PrependStatement]

        # fetch the bugzoo snapshot
        if 'snapshot' not in yml:
            raise BadConfigurationException("'snapshot' property is missing")
        if not isinstance(yml['snapshot'], str):
            m = "'snapshot' property should be a string"
            raise BadConfigurationException(m)
        name_snapshot = yml['snapshot']

        # connect to BugZoo
        logger.info("connecting to BugZoo server")
        with bugzoo.server.ephemeral() as client_bugzoo:
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
            localization = Localization.from_coverage(coverage, metric)
            logger.info("computed fault localization:\n%s", localization)

            # determine implicated files and lines
            files = localization.files
            lines = list(localization)  # type: List[FileLine]

            # compute analysis
            analysis = kaskara.Analysis.build(client_bugzoo,
                                              snapshot,
                                              files)

            # build problem
            problem = Problem(client_bugzoo,
                              snapshot,
                              coverage,
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

            # find all single-edit patches
            logger.info("constructing all single-edit patches...")
            candidates = list(all_single_edit_patches(tx))
            logger.info("constructed %d single-edit patches", len(candidates))

            # build the search strategy
            # FIXME pass time limit
            searcher = Searcher(bugzoo=problem.bugzoo,
                                problem=problem,
                                candidates=iter(candidates),
                                threads=threads,
                                candidate_limit=limit_candidates)

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

            # report stats
            num_test_evals = searcher.num_test_evals
            num_candidate_evals = searcher.num_candidate_evals
            time_running_mins = searcher.time_running.seconds / 60

            logger.info("found %d plausible patches", len(patches))
            logger.info("time taken: %.2f minutes", time_running_mins)
            logger.info("# test evaluations: %d", searcher.num_test_evals)
            logger.info("# candidate evaluations: %d", searcher.num_candidate_evals)


class CLI(cement.App):
    class Meta:
        label = 'darjeeling'
        handlers = [BaseController]


def main():
    log_to_stdout = logging.StreamHandler()
    log_to_stdout.setLevel(logging.DEBUG)
    # logger.addHandler(log_to_stdout)
    logging.getLogger('darjeeling').addHandler(log_to_stdout)

    with CLI() as app:
        app.run()
