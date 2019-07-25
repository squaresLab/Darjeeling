from typing import List, Optional, Dict, Any, Type
import logging
import logging.handlers
from datetime import datetime, timedelta
from glob import glob
import sys
import random
import warnings
import shutil
import os

import bugzoo
import cement
import yaml

from ..session import Session
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

    @property
    def _default_log_filename(self) -> str:
        # find all log file numbers that have been used in this directory
        used_numbers = [int(s.rpartition('.')[-1])
                        for s in glob('darjeeling.log.*')]

        if not used_numbers:
            return os.path.join(os.getcwd(), 'darjeeling.log.0')

        num = max(used_numbers) + 1
        return os.path.join(os.getcwd(), 'darjeeling.log.{}'.format(num))

    @cement.ex(
        help='attempt to automatically repair a given program',
        arguments=[
            (['filename'],
             {'help': ('a Darjeeling configuration file describing the faulty '
                       'program and how it should be repaired.') }),
            (['--log-to-file'],
             {'help': 'path to store the log file.',
              'type': str}),
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
        # setup logging to file
        log_to_filename = self.app.pargs.log_to_file  # type: Optional[str]
        if not log_to_filename:
            log_to_filename = self._default_log_filename
        logger.info("logging to file: %s", log_to_filename)

        log_formatter = logging.Formatter(
            '%(asctime)s:%(name)s:%(levelname)s: %(message)s',
            '%Y-%m-%d %H:%M:%S')
        log_to_file = \
            logging.handlers.WatchedFileHandler(log_to_filename, mode='w')
        log_to_file.setLevel(logging.DEBUG)
        log_to_file.setFormatter(log_formatter)
        logging.getLogger('darjeeling').addHandler(log_to_file)

        filename = self.app.pargs.filename  # type: str
        seed = self.app.pargs.seed  # type: Optional[int]
        terminate_early = self.app.pargs.terminate_early  # type: bool
        threads = self.app.pargs.threads  # type: Optional[int]
        limit_candidates = \
            self.app.pargs.limit_candidates  # type: Optional[int]
        limit_time_minutes = \
            self.app.pargs.limit_time_minutes  # type: Optional[int]

        with open(filename, 'r') as f:
            yml = yaml.safe_load(f)

        # connect to BugZoo
        logger.info("connecting to BugZoo server")
        with bugzoo.server.ephemeral(timeout_connection=120) as client_bugzoo:
            logger.info("connected to BugZoo server")
            try:
                session = Session.from_yml(
                    client_bugzoo,
                    yml,
                    threads=threads,
                    seed=seed,
                    terminate_early=terminate_early,
                    limit_candidates=limit_candidates,
                    limit_time_minutes=limit_time_minutes)
            except BadConfigurationException as err:
                logger.error(str(err))
                sys.exit(1)
            session.run()
            session.close()


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
