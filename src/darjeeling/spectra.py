# -*- coding: utf-8 -*-
__all__ = ('Spectra', 'SpectraRow')

from typing import Mapping, MutableMapping, Dict

import attr

from .core import TestCoverageMap, FileLine


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


class Spectra:
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

        for test in coverage:
            if test.outcome.successful:
                tally = tally_pass
                num_pass += 1
            else:
                tally = tally_fail
                num_fail += 1
            for line in coverage[test]:
                tally[line] = tally.get(line, 0) + 1

        return Spectra(num_pass, num_fail, tally_fail, tally_pass)

    def __init__(self,
                 num_passing: int,
                 num_failing: int,
                 tally_passing: Mapping[FileLine, int],
                 tally_failing: Mapping[FileLine, int]
                 ) -> None:
        self.__num_passing = num_passing
        self.__num_failing = num_failing
        self.__tally_passing: Dict[str, Dict[int, int]] = \
            FileLine.compactify(tally_passing)
        self.__tally_failing: Dict[str, Dict[int, int]] = \
            FileLine.compactify(tally_failing)
