# -*- coding: utf-8 -*-
__all__ = ('ProgramTransformations',)

from typing import Collection, Iterator, Optional
import typing

from loguru import logger
import attr

from .base import Transformation, TransformationSchema
from .database import TransformationDatabase
from .database.simple import SimpleTransformationDatabase
from ..core import FileLine
from ..util import Stopwatch

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
    _database: TransformationDatabase = \
        attr.ib(repr=False, eq=False, hash=False)

    @classmethod
    def build(cls,
              schemas: Collection[TransformationSchema],
              problem: 'Problem'
              ) -> 'ProgramTransformations':
        # TODO for now, use a single thread to construct the program
        # transformations. In the future, we can add an option that
        # allows users to use more threads.

        def find_transformations() -> Iterator['Transformation']:
            for schema in schemas:
                yield from schema.find_all(problem)

        with Stopwatch() as timer:
            logger.info("building transformation database")
            transformations = find_transformations()
            database = SimpleTransformationDatabase.build(transformations)
            logger.info("built transformation database "
                        f"(took {timer.duration:.3f} seconds)")

        return ProgramTransformations(schemas, database)

    def __len__(self) -> int:
        """Returns a count of the number of possible transformations."""
        return len(self._database)

    def __iter__(self) -> Iterator['Transformation']:
        """Returns an iterator over all possible transformations."""
        yield from self._database

    def choice(self) -> 'Transformation':
        """Selects a single transformation at random"""
        return self._database.choice()

    def find(self,
             *,
             schemas: Optional[Collection[TransformationSchema]] = None,
             lines: Optional[Collection[FileLine]] = None,
             ) -> Iterator[Transformation]:
        """
        Returns an iterator over all transformations that satisfy a given
        set of criteria.

        Parameters
        ----------
        schemas
            The schemas that were used to generate the transformations.
        lines
            The lines at which the transformations are applied.
        """
        if schemas is None:
            schemas = []
        if lines is None:
            lines = []

        raise NotImplementedError
