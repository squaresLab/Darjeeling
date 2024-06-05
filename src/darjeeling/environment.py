
from __future__ import annotations

__all__ = ("Environment",)

import os
from contextlib import ExitStack
from types import TracebackType

import attr
import dockerblade
from bugzoo import Client as BugZooClient
from bugzoo.server import ephemeral as bugzoo_server
from comby import Comby
from dockerblade import DockerDaemon
from loguru import logger

_DEFAULT_URL = os.environ.get("DOCKER_HOST", "unix://var/run/docker.sock")


@attr.s(auto_attribs=True, slots=True)
class Environment:
    _bugzoo: BugZooClient | None = attr.ib(default=None)
    _contexts: ExitStack = attr.ib(factory=ExitStack)
    comby: Comby = attr.ib(factory=Comby)
    docker_url: str = attr.ib(default=_DEFAULT_URL)
    dockerblade: DockerDaemon = attr.ib(init=False)

    def __attrs_post_init__(self) -> None:
        self.dockerblade = dockerblade.DockerDaemon(self.docker_url)

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

    def __enter__(self) -> Environment:
        return self

    def __exit__(
        self,
        ex_type: type[BaseException] | None,
        ex_val: BaseException | None,
        ex_tb: TracebackType | None,
    ) -> None:
        self.close()
