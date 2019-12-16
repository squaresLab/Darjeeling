# -*- coding: utf-8 -*-
__all__ = ('Environment',)

import attr
import bugzoo as _bugzoo
import dockerblade as _dockerblade


@attr.s(auto_attribs=True, slots=True)
class Environment:
    bugzoo: _bugzoo.Client
    dockerblade: _dockerblade.DockerDaemon = \
        attr.ib(factory=_dockerblade.DockerDaemon)
