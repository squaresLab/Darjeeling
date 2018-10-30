__all__ = ['Replacement', 'FileLine', 'FileLocationRange', 'Location']

from enum import Enum

from boggart.core.replacement import Replacement
from boggart.core.location import FileLocationRange, FileLine, Location, \
                                  LocationRange, FileLocation, FileLineSet


class Language(Enum):
    C = 'c'
    CPP = 'cpp'
    TEXT = 'text'
