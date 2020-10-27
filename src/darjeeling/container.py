# -*- coding: utf-8 -*-
__all__ = ('ProgramContainer',)

import typing
from typing import Optional

import attr
import dockerblade as _dockerblade
from bugzoo.core.patch import Patch as BugZooPatch

from . import exceptions as exc
from .environment import Environment

if typing.TYPE_CHECKING:
    from .program import ProgramDescription


@attr.s(frozen=True, slots=True, auto_attribs=True, repr=False)
class ProgramContainer:
    """Provides access to a container for a program variant."""
    id: str
    program: 'ProgramDescription'
    _environment: Environment
    _dockerblade: _dockerblade.Container

    @staticmethod
    def for_program(environment: Environment,
                    program: 'ProgramDescription'
                    ) -> 'ProgramContainer':
        dockerblade = environment.dockerblade.provision(program.image)
        return ProgramContainer(id=dockerblade.id,
                                program=program,
                                environment=environment,
                                dockerblade=dockerblade)

    def __repr__(self) -> str:
        return f'ProgramContainer(id={self.id})'

    def __enter__(self) -> 'ProgramContainer':
        return self

    def __exit__(self, exception_type, exception_value, traceback) -> None:
        self.close()

    def close(self) -> None:
        self._dockerblade.remove()

    def patch(self, patch: BugZooPatch) -> None:
        """Applies a given patch to this container.

        Raises
        ------
        FailedToApplyPatch
            if the patch was not successfully applied.
        """
        context = self.program.source_directory
        unified_diff = str(patch)
        try:
            self.filesystem.patch(context=context, diff=unified_diff)
        except _dockerblade.CalledProcessError:
            raise exc.FailedToApplyPatch

    @property
    def shell(self) -> _dockerblade.Shell:
        return self._dockerblade.shell('/bin/bash')

    @property
    def filesystem(self) -> _dockerblade.FileSystem:
        return self._dockerblade.filesystem()

    @property
    def ip_address(self) -> str:
        """The local IP address assigned to this container."""
        ip_address: Optional[str] = self._dockerblade.ip_address
        if not ip_address:
            m = f"unable to obtain IP address for container: {self}"
            raise exc.UnableToObtainIpAddress(m)
        return ip_address
