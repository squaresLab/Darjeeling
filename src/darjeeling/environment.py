# -*- coding: utf-8 -*-
__all__ = ('Environment',)

from contextlib import ExitStack
from types import TracebackType
from typing import Optional, Type

import attr
from bugzoo import Client as BugZooClient
from bugzoo.server import ephemeral as bugzoo_server
from comby import Comby
from dockerblade import DockerDaemon
from loguru import logger


@attr.s(auto_attribs=True, slots=True)
class Environment:
    _bugzoo: Optional[BugZooClient] = attr.ib(default=None)
    _contexts: ExitStack = attr.ib(factory=ExitStack)
    comby: Comby = attr.ib(factory=Comby)
    dockerblade: DockerDaemon = attr.ib(factory=DockerDaemon)

    @property
    def bugzoo(self) -> BugZooClient:
        logger.debug("connecting to BugZoo server")
        if self._bugzoo is None:
            self._bugzoo = self._contexts.enter_context(bugzoo_server(timeout_connection=120))
        logger.debug("connected to BugZoo server")
        return self._bugzoo

    def close(self) -> None:
        self._bugzoo = None
        self.dockerblade.close()
        self._contexts.close()

    def __enter__(self) -> 'Environment':
        return self

    def __exit__(
        self,
        ex_type: Optional[Type[BaseException]],
        ex_val: Optional[BaseException],
        ex_tb: Optional[TracebackType],
    ) -> None:
        self.close()
