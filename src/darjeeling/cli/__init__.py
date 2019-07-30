from typing import List, Optional, Dict, Any, Type, Sequence, Tuple, Union
import logging
import logging.handlers
from datetime import datetime, timedelta
from glob import glob
from threading import Thread, Event
import sys
import random
import warnings
import shutil
import os

import bugzoo
import cement
import pyroglyph
import attr
import yaml

from ..problem import Problem
from ..version import __version__ as VERSION
from ..session import Session
from ..exceptions import BadConfigurationException
from ..util import duration_str

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)

BANNER = 'DARJEELING'


@attr.s
class ResourcesBlock(pyroglyph.Block):
    session: Session = attr.ib()

    @property
    def title(self) -> str:
        return 'Resources Used'

    @property
    def contents(self) -> Sequence[str]:
        duration_s: str = duration_str(self.session.running_time_secs)
        l_time = f'Running Time: {duration_s}'
        l_candidates = f'Num. Candidates: {self.session.num_candidate_evaluations}'
        l_patches = 'Num. Acceptable Patches: TODO'
        return [l_time, l_candidates, l_patches]


class ProblemBlock(pyroglyph.BasicBlock):
    def __init__(self, problem: Problem) -> None:
        title = f'Problem [{problem.bug.name}]'
        num_failing = len(list(problem.failing_tests))
        num_passing = len(list(problem.passing_tests))
        num_lines = len(list(problem.lines))
        num_files = len(list(problem.implicated_files))
        contents = [
            f'Passing Tests: {num_passing}',
            f'Failing Tests: {num_failing}',
            f'Implicated Lines: {num_lines} ({num_files} files)'
        ]
        super().__init__(title, contents)


class UI(pyroglyph.Window):
    def __init__(self, session: Session, **kwargs) -> None:
        title = f' Darjeeling [v{VERSION}] '
        blocks_left = [ResourcesBlock(session)]
        blocks_right = [ProblemBlock(session.problem)]
        super().__init__(title, blocks_left, blocks_right, **kwargs)


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
            (['--interactive'],
             {'help': 'enables an interactive user interface.',
              'action': 'store_true'}),
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
        # setup logging to stdout
        log_to_stdout = logging.StreamHandler()
        log_to_stdout.setLevel(logging.INFO)
        logging.getLogger('darjeeling').addHandler(log_to_stdout)

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
        interactive = self.app.pargs.interactive  # type: bool
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

            if interactive:
                log_to_stdout.setLevel(logging.CRITICAL)
                with UI(session):
                    session.run()
                    session.close()

            if not interactive:
                session.run()
                session.close()


class CLI(cement.App):
    class Meta:
        label = 'darjeeling'
        handlers = [BaseController]


def main():
    with CLI() as app:
        app.run()
