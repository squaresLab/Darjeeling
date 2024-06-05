from __future__ import annotations

__all__ = (
    "TemplateTransformationSchema",
    "TemplateTransformationSchemaConfig",
)

import typing
from typing import Any, ClassVar, NoReturn

import attr
from overrides import overrides

import darjeeling.exceptions as exc
from darjeeling.transformation.base import Transformation, TransformationSchema
from darjeeling.transformation.config import TransformationSchemaConfig

if typing.TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from comby import Comby

    from darjeeling.problem import Problem
    from darjeeling.snippet import SnippetDatabase


@attr.s(auto_attribs=True)
class TemplateTransformationSchema(TransformationSchema):  # type: ignore[type-arg]
    _problem: Problem = attr.ib(repr=False, eq=False, hash=False)
    _comby: Comby = attr.ib(repr=False, eq=False, hash=False)
    match: str
    rewrite: str

    def find_all_in_file(self, filename: str) -> Iterator[Transformation]:
        m = ("template-based transformations should be supported in "
             "Darjeeling within the next few days (Dec. 6, 2020).")
        raise NotImplementedError(m)


@attr.s(frozen=True, auto_attribs=True)
class TemplateTransformationSchemaConfig(TransformationSchemaConfig):
    NAME: ClassVar[str] = "template"

    match: str
    rewrite: str

    @classmethod
    @overrides
    def from_dict(
        cls,
        dict_: Mapping[str, Any],
        dir_: str | None = None,
    ) -> TransformationSchemaConfig:
        def err(message: str) -> NoReturn:
            raise exc.BadConfigurationException(message)

        def read_string_property(name: str) -> str:
            if name not in dict_:
                err(f'missing "{name}" property in template transformation config')

            value = dict_[name]

            if not isinstance(value, str):
                err(f'expected "{name}" property in template transformation config'
                    f' to be a str but was a {value.__class__.__name__}')

            return value

        match = read_string_property("match")
        rewrite = read_string_property("rewrite")

        return TemplateTransformationSchemaConfig(
            match=match,
            rewrite=rewrite,
        )

    def build(
        self,
        problem: Problem,
        snippets: SnippetDatabase,  # type: ignore[type-arg]
    ) -> TransformationSchema:  # type: ignore[type-arg]
        return TemplateTransformationSchema(
            problem=problem,
            comby=problem.environment.comby,
            match=self.match,
            rewrite=self.rewrite,
        )
