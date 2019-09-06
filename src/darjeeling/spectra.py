# -*- coding: utf-8 -*-
__all__ = ('Spectra', 'SpectraRow')

from typing import Mapping, TypeVar

import attr

T = TypeVar('T')


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


class Spectra(Mapping[T, SpectraRow]):
    def __len__(self) -> int:
        return len(self.__contents)

    def __getitem__(self, loc: T) -> SpectraRow:
        return self.__contents[loc]

    def __iter__(self) -> Iterator[T]:
        yield from self.__contents
