# -*- coding: utf-8 -*-
__all__ = ('Spectra', 'SpectraRow')

from typing import Mapping, MutableMapping, Dict, Set, Iterator

import attr

from .core import TestCoverageMap, FileLine, FileLineMap, FileLineSet


@attr.s(frozen=True, slots=True, auto_attribs=True)
class SpectraRow:
    """
    Summarises coverage for a single program location in terms of the
    number of passing and failing tests that do and do not cover it,
    respectively.

    Attributes
    ----------
    ep: int
        The number of passing tests that cover this line.
    ef: int
        The number of failing tests that cover this line.
    np: int
        The number of passing tests that do not cover this line.
    nf: int
        The number of failing tests that do not cover this line.
    """
    ep: int
    ef: int
    np: int
    nf: int


class Spectra(Mapping[FileLine, SpectraRow]):
    """
    A summary of the number of passing and failing tests covering each program
    location.
    """
    @staticmethod
    def from_coverage(cov: TestCoverageMap) -> 'Spectra':
        num_fail = 0
        num_pass = 0
        tally_fail: MutableMapping[FileLine, int] = {}
        tally_pass: MutableMapping[FileLine, int] = {}

        for test_coverage in cov.values():
            if test_coverage.outcome.successful:
                tally = tally_pass
                num_pass += 1
            else:
                tally = tally_fail
                num_fail += 1
            for line in test_coverage:
                tally[line] = tally.get(line, 0) + 1

        return Spectra(num_pass, num_fail, tally_pass, tally_fail)

    def __init__(self,
                 num_pass: int,
                 num_fail: int,
                 tally_pass: Mapping[FileLine, int],
                 tally_fail: Mapping[FileLine, int]
                 ) -> None:
        self.__num_pass = num_pass
        self.__num_fail = num_fail
        self.__tally_pass: Mapping[FileLine, int] = FileLineMap(tally_pass)
        self.__tally_fail: Mapping[FileLine, int] = FileLineMap(tally_fail)
        self.__locations: Set[FileLine] = \
            FileLineSet.from_iter(tally_pass).union(tally_fail)

    def __getitem__(self, loc: FileLine) -> SpectraRow:
        """Retrieves the spectra information for a given location."""
        ep = self.__tally_pass.get(loc, 0)
        ef = self.__tally_fail.get(loc, 0)
        np = self.__num_pass - ep
        nf = self.__num_fail - ef
        return SpectraRow(ep, ef, np, nf)

    def __iter__(self) -> Iterator[FileLine]:
        """Returns an iterator over the locations in this spectra."""
        yield from self.__locations

    def __len__(self) -> int:
        """Returns a count of the number of locations in this spectra."""
        return len(self.__locations)
