import logging
import datetime
import sys

import bugzoo
import cement
import yaml

from ..exceptions import BadConfigurationException

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

        # connect to BugZoo


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

        # fetch the bugzoo snapshot
        if 'snapshot' not in yml:
            raise BadConfigurationException("'snapshot' property is missing")
        if not isinstance(yml['snapshot'], str):
            m = "'snapshot' property should be a string."
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
