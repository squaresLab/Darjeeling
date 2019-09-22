# -*- coding: utf-8 -*-
import logging as _logging
import importlib as _importlib
import pkgutil as _pkgutil

from . import exceptions
from .version import __version__
from .problem import Problem

_logging.getLogger(__name__).setLevel(_logging.INFO)
_logging.getLogger(__name__).addHandler(_logging.NullHandler())

# TODO dynamically load plugins
