# -*- coding: utf-8 -*-
__all__ = ('CsvEventLogger',)

from typing import Sequence, TextIO
from typing_extensions import Protocol
import os
import csv

import attr

from .event import DarjeelingEvent
from .handler import DarjeelingEventHandler


class _CSVWriter(Protocol):
    def writerow(self, row: Sequence[str]) -> None:
        ...


@attr.s(eq=False, hash=False)
class CsvEventLogger(DarjeelingEventHandler):
    """Logs all events to a CSV file.

    Attributes
    ----------
    filename: str
        The absolute path to the file to which events should be relayed.
    """
    filename: str = attr.ib()
    _file: TextIO = attr.ib(init=False, repr=False)
    _writer: _CSVWriter = attr.ib(init=False, repr=False)

    @filename.validator
    def validate_filename(self, attr, value) -> None:
        if not os.path.isabs(self.filename):
            raise ValueError("'filename' must be an absolute path")

    def __attrs_post_init__(self) -> None:
        self._file = open(self.filename, 'w')
        self._writer = csv.writer(self._file)

    def notify(self, event: DarjeelingEvent) -> None:
        print(str(event))
