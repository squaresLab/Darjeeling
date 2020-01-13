# -*- coding: utf-8 -*-
from typing import (List, Optional, Dict, Any, Type, Sequence, Tuple, Union,
                    Callable)
import logging
import logging.handlers
from datetime import datetime, timedelta
from glob import glob
from threading import Thread, Event
import json
import sys
import random
import warnings
import shutil
import os

from loguru import logger
import bugzoo
import bugzoo.server
import cement
import pyroglyph
import attr
import yaml

from ..environment import Environment
from ..problem import Problem
from ..version import __version__ as VERSION
from ..core import TestCoverageMap
from ..config import Config
from ..events import CsvEventLogger
from ..session import Session
from ..exceptions import BadConfigurationException
from ..util import duration_str

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
        help='generates a test suite coverage report for a given problem',
        arguments=[
            (['filename'],
             {'help': ('a Darjeeling configuration file describing a faulty '
                       'program and how it should be repaired.') }),
            (['--format'],
             {'help': 'the format that should be used for the coverage report',
              'default': 'text',
              'choices': ('text', 'yaml', 'json')})
        ]
    )
    def coverage(self) -> None:
        """Generates a coverage report for a given program."""
        # load the configuration file
        filename = self.app.pargs.filename
        filename = os.path.abspath(filename)
        cfg_dir = os.path.dirname(filename)
        with open(filename, 'r') as f:
            yml = yaml.safe_load(f)
        cfg = Config.from_yml(yml, dir_=cfg_dir)

        with bugzoo.server.ephemeral(timeout_connection=120) as client_bugzoo:
            environment = Environment(bugzoo=client_bugzoo)
            try:
                session = Session.from_config(environment, cfg)
            except BadConfigurationException as err:
                print("ERROR: bad configuration file")
                sys.exit(1)

            coverage = session.coverage
            formatter = ({
                'text': lambda c: str(c),
                'yaml': lambda c: yaml.safe_dump(c.to_dict(), default_flow_style=False),
                'json': lambda c: json.dumps(c.to_dict(), indent=2)
            })[self.app.pargs.format]
            print(formatter(coverage))

    @cement.ex(
        help='attempt to automatically repair a given program',
        arguments=[
            (['filename'],
             {'help': ('a Darjeeling configuration file describing the faulty '
                       'program and how it should be repaired.') }),
            (['--interactive'],
             {'help': 'enables an interactive user interface.',
              'action': 'store_true'}),
            (['--silent'],
             {'help': 'prevents output to the stdout',
              'action': 'store_true'}),
            (['--log-events-to-file'],
             {'help': 'path of the CSV file to which events should be logged.',
              'type': str}),
            (['--print-patch'],
             {'help': 'prints the first acceptable patch that was found',
              'action': 'store_true'}),
            (['--log-to-file'],
             {'help': 'path to store the log file.',
              'type': str}),
            (['--patch-dir'],
             {'help': 'path to store the patches.',
              'dest': 'dir_patches',
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
    def repair(self) -> bool:
        """Performs repair on a given scenario.

        Returns
        -------
        bool
            :code:`True` if at least one patch was found, else :code:`False`.
        """
        filename: str = self.app.pargs.filename
        interactive: bool = self.app.pargs.interactive
        seed: Optional[int] = self.app.pargs.seed
        terminate_early: bool = self.app.pargs.terminate_early
        threads: Optional[int] = self.app.pargs.threads
        limit_candidates: Optional[int] = \
            self.app.pargs.limit_candidates
        limit_time_minutes: Optional[int] = \
            self.app.pargs.limit_time_minutes
        dir_patches: Optional[str] = self.app.pargs.dir_patches
        log_to_filename: Optional[str] = self.app.pargs.log_to_file

        # remove all existing loggers
        logger.remove()
        logger.enable('darjeeling')

        # log to stdout, unless instructed not to do so
        if not self.app.pargs.silent:
            logger.add(sys.stdout,
                       level=('CRITICAL' if interactive else 'INFO'))

        # setup logging to file
        if not log_to_filename:
            log_to_filename = self._default_log_filename
        logger.info(f'logging to file: {log_to_filename}')
        logger.add(log_to_filename, level='DEBUG')

        # load the configuration file
        filename = os.path.abspath(filename)
        cfg_dir = os.path.dirname(filename)
        with open(filename, 'r') as f:
            yml = yaml.safe_load(f)
        cfg = Config.from_yml(yml,
                              dir_=cfg_dir,
                              threads=threads,
                              seed=seed,
                              terminate_early=terminate_early,
                              limit_candidates=limit_candidates,
                              limit_time_minutes=limit_time_minutes,
                              dir_patches=dir_patches)
        logger.info(f"using configuration: {cfg}")

        # connect to BugZoo
        logger.info("connecting to BugZoo server")
        with bugzoo.server.ephemeral(timeout_connection=120) as client_bugzoo:
            logger.info("connected to BugZoo server")
            environment = Environment(bugzoo=client_bugzoo)
            try:
                session = Session.from_config(environment, cfg)
            except BadConfigurationException as err:
                logger.error(str(err))
                sys.exit(1)

            # create and attach handlers
            if self.app.pargs.log_events_to_file:
                csv_logger_fn = self.app.pargs.log_events_to_file
                if not os.path.isabs(csv_logger_fn):
                    csv_logger_fn = os.path.join(os.getcwd(), csv_logger_fn)
                csv_logger = CsvEventLogger(csv_logger_fn,
                                            session._problem)
                session.attach_handler(csv_logger)

            if interactive:
                with UI(session):
                    session.run()
                    session.close()

            if not interactive:
                session.run()
                session.close()

            if self.app.pargs.print_patch and session.has_found_patch:
                first_patch = next(session.patches)
                print(str(first_patch))

            if session.has_found_patch:
                sys.exit(0)
            else:
                sys.exit(1)


class CLI(cement.App):
    class Meta:
        label = 'darjeeling'
        catch_signals = None
        handlers = [BaseController]


def main():
    with CLI() as app:
        app.run()
