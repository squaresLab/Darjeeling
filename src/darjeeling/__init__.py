# -*- coding: utf-8 -*-
import logging as _logging
import importlib as _importlib
import pkgutil as _pkgutil

from . import exceptions
from .version import __version__
from .problem import Problem

_logging.getLogger(__name__).setLevel(_logging.INFO)
_logging.getLogger(__name__).addHandler(_logging.NullHandler())


def _load_plugins() -> None:
    """Dynamically loads all plugins for Darjeeling."""
    for finder, name, is_pkg in _pkgutil.iter_modules():
        if name.startswith('darjeeling_'):
            _importlib.import_module(name)


_load_plugins()
