# -*- coding: utf-8 -*-
__all__ = ('ProgramTransformations',)

from typing import Collection, Dict, Iterator, List, Mapping, Sequence
import random
import typing

from loguru import logger
import attr

from .base import Transformation, TransformationSchema
from ..core import FileLine
from ..snippet import SnippetDatabase
from ..localization import Localization

if typing.TYPE_CHECKING:
    from ..problem import Problem


@attr.s
class ProgramTransformations:
    """Represents the space of possible transformations to a given program.

    Attributes
    ----------
    schemas: Collection[TransformationSchema]
        The schemas that compose the space of transformations.
    """
    schemas: Collection[TransformationSchema] = attr.ib()
    _transformations: Sequence[Transformation] = \
        attr.ib(repr=False, eq=False, hash=False)

    @classmethod
    def build(cls,
              schemas: Collection[TransformationSchema],
              problem: 'Problem',
              snippets: SnippetDatabase,
              localization: Localization
              ) -> 'ProgramTransformations':
        logger.debug("generating program transformations")
        transformations: List[Transformation] = []
        implicated_lines = list(localization)
        for schema in schemas:
            line_to_transformations = schema.all_at_lines(implicated_lines)
            for line in line_to_transformations:
                transformations += line_to_transformations[line]
        logger.debug("generated program transformations")
        return ProgramTransformations(schemas, transformations)

    def __len__(self) -> int:
        """Returns a count of the number of possible transformations."""
        return len(self._transformations)

    def __iter__(self) -> Iterator[Transformation]:
        """Returns an iterator over all possible transformations."""
        yield from self._transformations

    def choice(self) -> Transformation:
        """Selects a single transformation at random"""
        return random.choice(self._transformations)

    def sample(self, number: int) -> List[Transformation]:
        """Samples a number of transformations at random."""
        assert number > 0
        return random.sample(self._transformations, number)
