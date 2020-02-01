# -*- coding: utf-8 -*-
__all__ = ('TransformationIndex',)

from typing import Dict, Collection, Iterator, Iterable, List
import random
import typing

from loguru import logger
import attr

from .base import Transformation, TransformationSchema
from ..core import FileLine
from ..snippet import SnippetDatabase

if typing.TYPE_CHECKING:
    from ..problem import Problem

_Index = Dict[TransformationSchema, Dict[str, Dict[int, List[Transformation]]]]


@attr.s(repr=False)
class TransformationIndex(Iterable[Transformation]):
    _index: _Index = attr.ib(factory=dict)
    _length: int = attr.ib(init=False)

    @classmethod
    def build(cls,
              schemas: Collection[TransformationSchema],
              problem: 'Problem',
              snippets: SnippetDatabase,
              lines: List[FileLine]
              ) -> 'TransformationIndex':
        logger.debug("generating transformation index")
        index = TransformationIndex()
        for schema in schemas:
            line_to_transformations = schema.all_at_lines(lines)
            for line in line_to_transformations:
                index.insert(schema, line_to_transformations[line])
        logger.debug("generated transformation index")
        return index

    def __attrs_post_init__(self) -> None:
        self._length = sum(1 for transformation in self)

    def __iter__(self) -> Iterator[Transformation]:
        """Returns an iterator over the transformations in this index."""
        for schema_index in self._index.values():
            for file_index in schema_index.values():
                for line_index in file_index.values():
                    yield from line_index

    def __len__(self) -> int:
        """Returns a count of the number of transformations in this index."""
        return self._length

    def choice(self) -> Transformation:
        """Selects a single transformation at random"""
        # FIXME this is a horrifically slow implementation
        i = random.randint(0, self._length - 1)
        for j, transformation in enumerate(self):
            if i == j:
                return transformation
        # FIXME this isn't possible
        return transformation

    def restrict_to_file(self, filename: str) -> 'TransformationIndex':
        """Returns a variant of this index that is restricted to a given file."""  # noqa
        new_index: _Index = {}
        for schema in self._index:
            schema_file_index = {filename: self._index[schema][filename]}
            new_index[schema] = schema_file_index
        return TransformationIndex(new_index)

    def restrict_to_line(self, line: FileLine) -> 'TransformationIndex':
        """Returns a variant of this index that is restricted to a given line."""  # noqa
        filename = line.filename
        new_index: _Index = self.restrict_to_file(filename)._index
        for schema in new_index:
            schema_file_line_index = new_index[schema][filename][line.num]
            new_index[schema][filename] = {line.num: schema_file_line_index}
        return TransformationIndex(new_index)

    def restrict_to_schema(self,
                           schema: TransformationSchema
                           ) -> 'TransformationIndex':
        """Returns a variant of this index that is restricted to a given schema."""  # noqa
        return TransformationIndex({schema: self._index[schema]})

    def insert(self,
               schema: TransformationSchema,
               transformations: Iterable[Transformation]
               ) -> None:
        """Inserts transformations into this index.

        Arguments
        ---------
        schema: TransformationSchema
            The schema used to generate the transformations.
        transformations: Iterable[Transformation]
            The transformations that should be inserted.
        """
        if schema not in self._index:
            self._index[schema] = {}
        schema_index = self._index[schema]

        for transformation in transformations:
            self._length += 1
            line = transformation.line
            if line.filename not in schema_index:
                schema_index[line.filename] = {}
            file_index = schema_index[line.filename]

            if line.num not in file_index:
                file_index[line.num] = [transformation]
            else:
                file_index[line.num].append(transformation)
