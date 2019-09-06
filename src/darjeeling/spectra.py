# -*- coding: utf-8 -*-
__all__ = ('Spectra', 'SpectraRow')

import attr


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
    pass
