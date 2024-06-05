from __future__ import annotations

__all__ = ("Candidate",)

import typing

import attr
from bugzoo.core.patch import Patch

from darjeeling.core import FileLine, Replacement
from darjeeling.util import tuple_from_iterable

if typing.TYPE_CHECKING:
    from darjeeling.problem import Problem
    from darjeeling.transformation import Transformation


@attr.s(frozen=True, repr=False, slots=True, auto_attribs=True)
class Candidate:
    """Represents a repair as a set of atomic program transformations."""
    problem: Problem = attr.ib(hash=False, eq=False)
    transformations: tuple[Transformation, ...] = \
        attr.ib(converter=tuple_from_iterable)

    def to_diff(self) -> Patch:
        """Transforms this candidate patch into a concrete, unified diff."""
        replacements = \
            map(lambda t: t.to_replacement(), self.transformations)
        replacements_by_file: dict[str, list[Replacement]] = {}
        for rep in replacements:
            fn = rep.location.filename
            if fn not in replacements_by_file:
                replacements_by_file[fn] = []
            replacements_by_file[fn].append(rep)
        # FIXME order each collection of replacements by location
        return self.problem.sources.replacements_to_diff(replacements_by_file)

    def lines_changed(self) -> list[FileLine]:
        """Returns a list of source lines that are changed by this candidate
        patch.
        """
        return [t.line for t in self.transformations]

    @property
    def id(self) -> str:
        """An eight-character hexadecimal identifier for this candidate."""
        hex_hash = hex(abs(hash(self)))
        return hex_hash[2:10]

    def __repr__(self) -> str:
        return f"Candidate<#{self.id}>"
