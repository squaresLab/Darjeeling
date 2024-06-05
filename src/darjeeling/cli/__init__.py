from __future__ import annotations

import glob
import json
import os
import sys
from typing import Optional

import bugzoo
import bugzoo.server
import cement
import yaml
from loguru import logger

from darjeeling.config import Config
from darjeeling.environment import Environment
from darjeeling.events.csv_event_logger import CsvEventLogger
from darjeeling.events.websocket_event_handler import WebSocketEventHandler
from darjeeling.exceptions import BadConfigurationException
from darjeeling.plugins import LOADED_PLUGINS
from darjeeling.session import Session
from darjeeling.version import __version__ as VERSION

BANNER = "DARJEELING"


class BaseController(cement.Controller):  # type: ignore
    class Meta:
        label = "base"
        description = "Language-independent automated program repair"
        arguments = [
            (["--version"], {"action": "version", "version": BANNER}),
        ]

    def default(self):
        # type: () -> None
        self.app.args.print_help()

    @property
    def _default_log_filename(self) -> str:
        # find all log file numbers that have been used in this directory
        used_numbers = [int(s.rpartition(".")[-1])
                        for s in glob.glob("darjeeling.log.*")]

        if not used_numbers:
            return os.path.join(os.getcwd(), "darjeeling.log.0")

        num = max(used_numbers) + 1
        return os.path.join(os.getcwd(), f"darjeeling.log.{num}")

    @cement.ex(
        help="generates a test suite coverage report for a given problem",
        arguments=[
            (["filename"],
             {"help": ("a Darjeeling configuration file describing a faulty "
                       "program and how it should be repaired.")}),
            (["--format"],
             {"help": "the format that should be used for the coverage report",
              "default": "text",
              "choices": ("text", "yaml", "json")}),
        ],
    )  # type: ignore
    def coverage(self) -> None:
        """Generates a coverage report for a given program."""
        # load the configuration file
        filename = self.app.pargs.filename
        filename = os.path.abspath(filename)
        cfg_dir = os.path.dirname(filename)
        with open(filename) as f:
            yml = yaml.safe_load(f)
        cfg = Config.from_yml(yml, dir_=cfg_dir)

        with bugzoo.server.ephemeral(timeout_connection=120) as client_bugzoo:
            environment = Environment(bugzoo=client_bugzoo)
            try:
                session = Session.from_config(environment, cfg)
            except BadConfigurationException:
                print("ERROR: bad configuration file")
                sys.exit(1)

            coverage = session.coverage
            formatter = ({
                "text": lambda c: str(c),
                "yaml": lambda c: yaml.safe_dump(c.to_dict(), default_flow_style=False),
                "json": lambda c: json.dumps(c.to_dict(), indent=2),
            })[self.app.pargs.format]
            print(formatter(coverage))  # type: ignore

    @cement.ex(
        help="attempt to automatically repair a given program",
        arguments=[
            (["filename"],
             {"help": ("a Darjeeling configuration file describing the faulty "
                       "program and how it should be repaired.")}),
            (["--silent"],
             {"help": "prevents output to the stdout",
              "action": "store_true"}),
            (["--log-events-to-file"],
             {"help": "path of the CSV file to which events should be logged.",
              "type": str}),
            (["--print-patch"],
             {"help": "prints the first acceptable patch that was found",
              "action": "store_true"}),
            (["--log-to-file"],
             {"help": "path to store the log file.",
              "type": str}),
            (["--no-log-to-file"],
             {"help": "disables logging to file.",
              "action": "store_true"}),
            (["--patch-dir"],
             {"help": "path to store the patches.",
              "dest": "dir_patches",
              "type": str}),
            (["-v", "--verbose"],
             {"help": "enables verbose DEBUG-level logging to the stdout",
              "action": "store_true"}),
            (["--web"],
             {"help": "enables a web interface",
              "action": "store_true"}),
            (["--seed"],
             {"help": "random number generator seed",
              "type": int}),
            (["--max-candidates"],
             {"dest": "limit_candidates",
              "type": int,
              "help": ("the maximum number of candidate patches that may be "
                       "considered by the search.")}),
            (["--max-time-mins"],
             {"dest": "limit_time_minutes",
              "type": int,
              "help": ("the maximum number of minutes that may be spent "
                       "searching for a patch.")}),
            (["--continue"],
             {"dest": "terminate_early",
              "action": "store_false",
              "help": ("continue to search for patches after an acceptable "
                       " patch has been discovered.")}),
            (["--threads"],
             {"dest": "threads",
              "type": int,
              "help": ("number of threads over which the repair workload "
                       "should be distributed")}),
        ],
    )  # type: ignore
    def repair(self) -> bool:
        """Performs repair on a given scenario.

        Returns
        -------
        bool
            :code:`True` if at least one patch was found, else :code:`False`.
        """
        filename: str = self.app.pargs.filename
        seed: Optional[int] = self.app.pargs.seed
        terminate_early: bool = self.app.pargs.terminate_early
        threads: Optional[int] = self.app.pargs.threads
        limit_candidates: Optional[int] = \
            self.app.pargs.limit_candidates
        limit_time_minutes: Optional[int] = \
            self.app.pargs.limit_time_minutes
        dir_patches: Optional[str] = self.app.pargs.dir_patches
        log_to_filename: Optional[str] = self.app.pargs.log_to_file
        should_log_to_file: bool = not self.app.pargs.no_log_to_file
        verbose_logging: bool = self.app.pargs.verbose

        # remove all existing loggers
        logger.remove()
        logger.enable("darjeeling")
        for plugin_name in LOADED_PLUGINS:
            logger.enable(plugin_name)

        # log to stdout, unless instructed not to do so
        if not self.app.pargs.silent:
            if verbose_logging:
                stdout_logging_level = "TRACE"
            else:
                stdout_logging_level = "INFO"
            logger.enable("kaskara")
            logger.add(sys.stdout, level=stdout_logging_level)

        # setup logging to file
        if should_log_to_file:
            if not log_to_filename:
                log_to_filename = self._default_log_filename
            logger.info(f"logging to file: {log_to_filename}")
            logger.add(log_to_filename, level="TRACE")

        # load the configuration file
        filename = os.path.abspath(filename)
        cfg_dir = os.path.dirname(filename)
        with open(filename) as f:
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
        with Environment() as environment:
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

            # add optional websocket handler
            if self.app.pargs.web:
                websocket_handler = WebSocketEventHandler()
                session.attach_handler(websocket_handler)

            session.run()
            session.close()

            if self.app.pargs.print_patch and session.has_found_patch:
                first_patch = next(session.patches)
                print(str(first_patch))

            if session.has_found_patch:
                sys.exit(0)
            else:
                sys.exit(1)


class CLI(cement.App):  # type: ignore
    class Meta:
        label = "darjeeling"
        catch_signals = None
        handlers = [BaseController]


def main() -> None:
    with CLI() as app:
        app.run()
