# -*- coding: utf-8 -*-
__all__ = ('Environment',)

import attr
import bugzoo as _bugzoo


@attr.s(auto_attribs=True, slots=True)
class Environment:
    bugzoo: _bugzoo.Client
