# -*- coding: utf-8 -*-
__all__ = ('ProgramContainer',)

import attr
import bugzoo as _bugzoo
import dockerblade as _dockerblade
from bugzoo.core.patch import Patch as BugZooPatch

from .environment import Environment
from .exceptions import FailedToApplyPatch


@attr.s(frozen=True, slots=True, auto_attribs=True, repr=False)
class ProgramContainer:
    """Provides access to a container for a program variant."""
    id: str
    _environment: Environment
    _bugzoo: _bugzoo.Container
    _dockerblade: _dockerblade.Container

    def __repr__(self) -> str:
        return f'ProgramContainer(id={self.id})'

    def __enter__(self) -> 'ProgramContainer':
        return self

    def __exit__(self, exception_type, exception_value, traceback) -> None:
        self.close()

    def close(self) -> None:
        mgr_ctr = self._environment.bugzoo.containers
        del mgr_ctr[self.id]

    @classmethod
    def for_bugzoo_snapshot(cls,
                            environment: Environment,
                            snapshot: _bugzoo.Bug
                            ) -> 'ProgramContainer':
        mgr_ctr = environment.bugzoo.containers
        container = mgr_ctr.provision(snapshot)
        try:
            return cls.from_bugzoo_container(environment, container)
        except:
            del mgr_ctr[container.uid]
            raise

    @classmethod
    def from_bugzoo_container(cls,
                              environment: Environment,
                              container: _bugzoo.Container
                              ) -> 'ProgramContainer':
        id = container.uid
        dockerblade_container = environment.dockerblade.attach(id)
        return ProgramContainer(id=id,
                                environment=environment,
                                bugzoo=container,
                                dockerblade=dockerblade_container)

    def patch(self, patch: BugZooPatch) -> None:
        """Applies a given patch to this container.
        
        Raises
        ------
        FailedToApplyPatch
            if the patch was not successfully applied.
        """
        mgr_ctr = self._environment.bugzoo.containers
        if not mgr_ctr.patch(self._bugzoo, patch):
            raise FailedToApplyPatch

    @property
    def shell(self) -> _dockerblade.Shell:
        return self._dockerblade.shell()

    @property
    def filesystem(self) -> _dockerblade.FileSystem:
        return self._dockerblade.filesystem()
