"""Defines a common interface that is implemented by all transformation databases."""
from __future__ import annotations

__all__ = ("TransformationDatabase",)

import abc
from collections.abc import Collection, Iterator

from darjeeling.transformation.base import Transformation


class TransformationDatabase(Collection[Transformation], abc.ABC):
    """Stores the set of possible transformations for a given program."""
    @abc.abstractmethod
    def __contains__(self, transformation: object) -> bool:
        """Determines if a given transformation belongs to this database."""
        ...

    @abc.abstractmethod
    def __iter__(self) -> Iterator[Transformation]:
        """Returns an iterator over all transformations in this database."""
        ...

    @abc.abstractmethod
    def __len__(self) -> int:
        """Returns the number of transformations in this database."""
        ...

    @abc.abstractmethod
    def choice(self) -> Transformation:
        """Selects a single transformation from this database at random."""
        ...
