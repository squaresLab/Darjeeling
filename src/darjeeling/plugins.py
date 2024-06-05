__all__ = ("LOADED_PLUGINS",)

import importlib as _importlib
import pkgutil as _pkgutil

from loguru import logger as _logger

LOADED_PLUGINS: list[str] = []


def _load_plugins() -> None:
    """Dynamically loads all plugins for Darjeeling."""
    for finder, name, is_pkg in _pkgutil.iter_modules():
        if name.startswith("darjeeling_"):
            _logger.info("loading plugin: %s", name)
            _importlib.import_module(name)
            LOADED_PLUGINS.append(name)


_load_plugins()
