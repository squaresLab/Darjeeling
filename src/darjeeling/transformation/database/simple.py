from __future__ import annotations

__all__ = ("SimpleTransformationDatabase",)

import random
import typing as t

import attr

from darjeeling.transformation.database.base import TransformationDatabase

if t.TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence

    from darjeeling.transformation.base import Transformation


@attr.s(repr=False, slots=True, frozen=True)
class SimpleTransformationDatabase(TransformationDatabase):
    """Uses a simple, inefficient tuple to store all transformations in memory without indexing."""
    _contents: Sequence[Transformation] = attr.ib(factory=tuple)

    @classmethod
    def build(cls,
              transformations: Iterable[Transformation],
              ) -> TransformationDatabase:
        contents: Sequence[Transformation] = tuple(transformations)
        return SimpleTransformationDatabase(contents)

    def __contains__(self, transformation: object) -> bool:
        """Determines if a given transformation belongs to this index."""
        return transformation in self._contents

    def __iter__(self) -> Iterator[Transformation]:
        """Returns an iterator over the transformations in this index."""
        yield from self._contents

    def __len__(self) -> int:
        """Returns a count of the number of transformations in this index."""
        return len(self._contents)

    def choice(self) -> Transformation:
        """Selects a single transformation at random."""
        return random.choice(self._contents)
