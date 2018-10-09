import logging
import datetime
import sys

import bugzoo
import cement
import yaml

from ..transformation.classic import DeleteStatement, \
                                     ReplaceStatement, \
                                     PrependStatement
from ..exceptions import BadConfigurationException
from ..problem import Problem
from ..localization import Localization, \
                           ample, \
                           genprog, \
                           jaccard, \
                           ochiai, \
                           tarantula
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
              'type': int})
        ]
    )
    def repair(self) -> None:
        filename = self.app.pargs.filename
        seed = self.app.pargs.seed

        with open(filename, 'r') as f:
            yml = yaml.load(f)

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
            seed = int(datetime.now())
            logger.info("using random number generator seed based on current date and time: %d",  # noqa: pycodestyle
                        seed)

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

            # TODO compute analysis
            analysis = None

            # build problem
            problem = Problem(client_bugzoo,
                              snapshot,
                              coverage,
                              analysis,
                              settings=settings)




class CLI(cement.App):
    class Meta:
        label = 'darjeeling'
        handlers = [BaseController]


def main():
    log_to_stdout = logging.StreamHandler()
    log_to_stdout.setLevel(logging.DEBUG)
    logger.addHandler(log_to_stdout)

    with CLI() as app:
        app.run()
