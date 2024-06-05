"""Provides base class used to describe transformation schema configurations.

The base class is a data structure for representing the configuration of
both individual transformation schemas and the overall space of transformations
that is used by the search, as well as methods for loading/saving those
configurations to and from dictionary-based formats (e.g., JSON, YAML, TOML).
"""
from __future__ import annotations

__all__ = ("TransformationSchemaConfig", "ProgramTransformationsConfig")

import abc
import typing
from typing import Any, NoReturn

import attr

import darjeeling.exceptions as exc
from darjeeling.transformation.transformations import ProgramTransformations
from darjeeling.util import dynamically_registered, tuple_from_iterable

if typing.TYPE_CHECKING:
    from collections.abc import Collection, Iterator, Mapping

    from darjeeling.problem import Problem
    from darjeeling.snippet import SnippetDatabase
    from darjeeling.transformation.base import TransformationSchema


@dynamically_registered(lookup="lookup")
class TransformationSchemaConfig(abc.ABC):
    """Describes a search algorithm configuration."""
    @classmethod
    def __iter__(cls) -> Iterator[str]:
        raise NotImplementedError

    @classmethod
    def __len__(cls) -> int:
        raise NotImplementedError

    @classmethod
    def lookup(cls, name: str) -> type[TransformationSchemaConfig]:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def from_dict(
        cls,
        d: Mapping[str, Any],
        dir_: str | None = None,
    ) -> TransformationSchemaConfig:
        name_type: str = d["type"]
        type_: type[TransformationSchemaConfig] = cls.lookup(name_type)
        return type_.from_dict(d, dir_)

    @abc.abstractmethod
    def build(
        self,
        problem: Problem,
        snippets: SnippetDatabase,  # type: ignore[type-arg]
    ) -> TransformationSchema:  # type: ignore[type-arg]
        ...


@attr.s(frozen=True)
class ProgramTransformationsConfig:
    """Describes the config used to obtain the set of all possible transformations.

    Attributes
    ----------
    schemas: Collection[TransformationSchemaConfig]
        The configuration for each schema used to compose the space of
        possible transformations.
    """
    schemas: Collection[TransformationSchemaConfig] = \
        attr.ib(converter=tuple_from_iterable)

    @classmethod
    def from_dict(
        cls,
        d: Mapping[str, Any],
        dir_: str | None = None,
    ) -> ProgramTransformationsConfig:
        def err(message: str) -> NoReturn:
            raise exc.BadConfigurationException(message)

        # load transformation schema configurations
        if "schemas" not in d:
            err('missing "schemas" property in "transformations" section')
        if not isinstance(d["schemas"], list):
            err('illegal "schemas" property: should be a list')
        if not d["schemas"]:
            err('illegal "schemas" property: '
                'must specify at least one schema')

        schemas: list[TransformationSchemaConfig] = []
        for d_schema in d["schemas"]:
            schema = TransformationSchemaConfig.from_dict(d_schema, dir_)
            schemas.append(schema)

        return ProgramTransformationsConfig(schemas=schemas)

    def build(
        self,
        problem: Problem,
        snippets: SnippetDatabase,  # type: ignore[type-arg]
    ) -> ProgramTransformations:
        """Constructs the transformation space described by this config."""
        schemas = [schema.build(problem, snippets) for schema in self.schemas]
        return ProgramTransformations.build(schemas, problem)
