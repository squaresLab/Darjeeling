# -*- coding: utf-8 -*-
__all__ = ('Candidate', 'all_single_edit_patches')

from typing import List, Iterator, Dict, FrozenSet, Iterable, Tuple
import typing

from loguru import logger
from bugzoo.core.patch import Patch
import attr

from .core import Replacement, FileLine
from .transformation import Transformation
from .util import tuple_from_iterable

if typing.TYPE_CHECKING:
    from .problem import Problem


@attr.s(frozen=True, repr=False, slots=True, auto_attribs=True)
class Candidate:
    """Represents a repair as a set of atomic program transformations."""
    problem: 'Problem' = attr.ib(hash=False, eq=False)
    transformations: Tuple[Transformation, ...] = \
        attr.ib(converter=tuple_from_iterable)

    def to_diff(self) -> Patch:
        """Transforms this candidate patch into a concrete, unified diff."""
        replacements = \
            map(lambda t: t.to_replacement(), self.transformations)
        replacements_by_file: Dict[str, List[Replacement]] = {}
        for rep in replacements:
            fn = rep.location.filename
            if fn not in replacements_by_file:
                replacements_by_file[fn] = []
            replacements_by_file[fn].append(rep)
        # FIXME order each collection of replacements by location
        return self.problem.sources.replacements_to_diff(replacements_by_file)

    def lines_changed(self) -> List[FileLine]:
        """
        Returns a list of source lines that are changed by this candidate
        patch.
        """
        replacements = \
            map(lambda t: t.to_replacement(), self.transformations)
        locations = [rep.location for rep in replacements]
        return [FileLine(loc.filename, loc.start.line) for loc in locations]

    @property
    def id(self) -> str:
        """An eight-character hexadecimal identifier for this candidate."""
        hex_hash = hex(abs(hash(self)))
        return hex_hash[2:10]

    def __repr__(self) -> str:
        return "Candidate<#{}>".format(self.id)


def all_single_edit_patches(problem: 'Problem',
                            transformations: Iterable[Transformation]
                            ) -> Iterator[Candidate]:
    """
    Returns an iterator over all of the single-edit patches that can be
    composed using a provided source of transformations.
    """
    logger.debug("finding all single-edit patches")
    for t in transformations:
        yield Candidate(problem, [t])
    logger.debug("exhausted all single-edit patches")
