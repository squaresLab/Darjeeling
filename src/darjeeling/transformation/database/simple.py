# -*- coding: utf-8 -*-
__all__ = ('SimpleTransformationDatabase',)

from typing import Iterator, Iterable, Sequence
import random
import typing

import attr

from .base import TransformationDatabase

if typing.TYPE_CHECKING:
    from ..base import Transformation


@attr.s(repr=False, slots=True, frozen=True)
class SimpleTransformationDatabase(TransformationDatabase):
    """
    Uses a simple, inefficient Python tuple to store all possible
    transformations within memory without any form of indexing to
    support faster querying.
    """
    _contents: Sequence['Transformation'] = attr.ib(factory=tuple)

    @classmethod
    def build(cls,
              transformations: Iterable['Transformation']
              ) -> TransformationDatabase:
        contents: Sequence['Transformation'] = tuple(transformations)
        return SimpleTransformationDatabase(contents)

    def __contains__(self, transformation: object) -> bool:
        """Determines if a given transformation belongs to this index."""
        return transformation in self._contents

    def __iter__(self) -> Iterator['Transformation']:
        """Returns an iterator over the transformations in this index."""
        yield from self._contents

    def __len__(self) -> int:
        """Returns a count of the number of transformations in this index."""
        return len(self._contents)

    def choice(self) -> 'Transformation':
        """Selects a single transformation at random"""
        return random.choice(self._contents)
