__all__ = ['Replacement', 'FileLine', 'FileLocationRange', 'Location']

from enum import Enum

from boggart.core.replacement import Replacement
from boggart.core.location import FileLocationRange, FileLine, Location, \
                                  LocationRange, FileLocation, FileLineSet

from .exceptions import LanguageNotSupported


class Language(Enum):
    @classmethod
    def find(cls, name: str) -> 'Language':
        try:
            return next(l for l in cls if l.value == name)
        except StopIteration:
            raise LanguageNotSupported(name)

    C = 'c'
    CPP = 'cpp'
    TEXT = 'text'
