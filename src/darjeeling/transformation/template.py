# -*- coding: utf-8 -*-
__all__ = ('TemplateTransformationSchema', 'TemplateTransformationSchemaConfig')

from typing import Iterator

import attr

from .base import Transformation, TransformationSchema
from .config import TemplateTransformationSchema


@attr.s(auto_attribs=True)
class TemplateTransformationSchema:
    _problem: 'Problem' = attr.ib(repr=False, eq=False, hash=False)
    _comby: 'CombyInterface' = attr.ib(repr=False, eq=False, hash=False)
    match: str
    rewrite: str

    def find_all_in_file(self, filename: str) -> Iterator[Transformation]:
        raise NotImplementedError


@attr.s(frozen=True, auto_attribs=True)
class TemplateTransformationSchemaConfig(TransformationSchemaConfig):
    match: str
    rewrite: str

    def build(self,
              problem: 'Problem',
              snippets: SnippetDatabase
              ) -> 'TransformationSchema':
        comby: CombyInterface = problem.environment.comby
        return TemplateTransformationSchema.build(
            problem=problem,
            comby=comby,
            match=self.match,
            rewrite=self.rewrite,
        )
