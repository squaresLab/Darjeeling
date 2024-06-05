from __future__ import annotations

__all__ = ("TestSuiteConfig",)

import abc
import typing
from typing import Any, NoReturn, Optional

from .. import exceptions as exc
from ..util import dynamically_registered

if typing.TYPE_CHECKING:
    from ..environment import Environment
    from .base import TestSuite


@dynamically_registered(lookup="lookup", length=None, iterator=None)
class TestSuiteConfig(abc.ABC):
    """Describes a test suite configuration."""
    @classmethod
    def lookup(cls, name: str) -> type[TestSuiteConfig]:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def from_dict(cls,
                  d: dict[str, Any],
                  dir_: Optional[str] = None,
                  ) -> TestSuiteConfig:
        def err(message: str) -> NoReturn:
            message = f"bad test suite configuration section: {message}"
            raise exc.BadConfigurationException(message)

        if "type" not in d:
            err('missing "type" property')
        if not isinstance(d["type"], str):
            err('"type" property must be a string')

        name_type: str = d["type"]
        type_: type[TestSuiteConfig] = TestSuiteConfig.lookup(name_type)
        return type_.from_dict(d, dir_)

    @abc.abstractmethod
    def build(
        self,
        environment: Environment,
    ) -> TestSuite:  # type: ignore
        """Builds the test suite described by this configuration."""
        ...
