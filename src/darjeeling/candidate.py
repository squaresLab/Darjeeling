# -*- coding: utf-8 -*-
__all__ = ('Candidate', 'DiffCandidate')

from typing import Dict, List, Tuple, Optional
import typing

from bugzoo.core.patch import Patch
import attr

from .core import (Replacement, FileLine)
from .transformation import Transformation
from .util import tuple_from_iterable

if typing.TYPE_CHECKING:
    from .problem import Problem


@attr.s(frozen=True, repr=False, slots=True, auto_attribs=True)
class Candidate:
    """Represents a repair as a set of atomic program transformations."""
    problem: 'Problem' = attr.ib(hash=False, eq=False)
    transformations: Optional[Tuple[Transformation, ...]] = \
        attr.ib(converter=tuple_from_iterable)

    def to_diff(self) -> Patch:
        """Transforms this candidate patch into a concrete, unified diff."""
        replacements = \
            map(lambda t: t.to_replacement(), self.transformations) if self.transformations else {}
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
        if self.transformations:
            return [t.line for t in self.transformations]
        else:
            return []

    @property
    def id(self) -> str:
        """An eight-character hexadecimal identifier for this candidate."""
        hex_hash = hex(abs(hash(self)))
        return hex_hash[2:10]

    def __repr__(self) -> str:
        return "Candidate<#{}>".format(self.id)


@attr.s(frozen=True, repr=False, slots=True, auto_attribs=True)
class DiffPatch:
    _file: str = attr.ib()
    _patch: Patch = attr.ib(factory=Patch)

    def to_diff(self) -> Patch:
        return self._patch

    @property
    def files(self) -> List[str]:
        return self._patch.files

    @property
    def patch(self) -> Patch:
        return self._patch

    @property
    def file_name(self) -> str:
        return self._file

    def __repr__(self) -> str:
        return "DiffPatch<{}>".format(self.file_name)


@attr.s(frozen=True, repr=False, slots=True, auto_attribs=True)
class DiffCandidate(Candidate):
    """Represents a repair as a set of atomic program transformations."""
    _diffpatch: DiffPatch = attr.ib()

    def lines_changed(self) -> List[FileLine]:
        locs: List[FileLine] = []
        # no accessibility to bugzoo.core.patch subcontent
        # lines = [(f.old_fn,l) for f in self.get_file_patches()\
        #          for h in f.__hunks \
        #          for l in range(h.__old_start_at,h.__old_start_at+len(h.__lines))\
        #         ]
        # for f,l in lines:
        #     locs.append(FileLine(f,l))
        return locs

    def to_diff(self) -> Patch:
        return self._diffpatch.to_diff()

    def get_file_patches(self):
        return self._diffpatch._patch.__file_patches

    @property
    def diffpatch(self) -> DiffPatch:
        return self._diffpatch

    @property
    def patch(self) -> Patch:
        return self._diffpatch.patch

    @property
    def file(self) -> str:
        return self._diffpatch.file_name

    @property
    def id(self) -> str:
        """An eight-character hexadecimal identifier for this candidate."""
        hex_hash = hex(abs(hash(self)))
        return hex_hash[2:10]

    def __repr__(self) -> str:
        return "DiffCandidate<{}#{}>".format(self.file, self.id)
