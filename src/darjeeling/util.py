import warnings
from typing import List, Union, Tuple
from timeit import default_timer as timer


def duration_tuple(secs: Union[int, float]) -> Tuple[int, int, int, int]:
    """Converts seconds into a tuple of days, hours, minutes, secs."""
    secs = int(secs)
    days, secs = divmod(secs, 86400)
    hours, secs = divmod(secs, 3600)
    mins, secs = divmod(secs, 60)
    return (secs, mins, hours, days)


def duration_str(secs: Union[int, float]) -> str:
    """Creates a duration string from a number of seconds.

    Example
    -------
    14 d 18 h 39 m 29 s
    """
    secs, mins, hours, days = duration_tuple(secs)
    return f'{days:2d} d {hours:2d} h {mins:2d} m {secs:2d} s'


def get_file_contents(fn: str) -> str:
    try:
        with open(fn, 'r') as f:
            return f.read()
    except UnicodeDecodeError:
        pass

    # let's try to decode the using latin-1 encoding
    with open(fn, 'r', encoding='latin-1') as f:
        return f.read()


def get_lines(fn: str) -> List[str]:
    """
    Attempts to return a list of all the lines in a given source code file.
    """
    return [l.rstrip('\n') for l in get_file_contents(fn).splitlines()]


class Stopwatch(object):
    def __init__(self) -> None:
        """
        Constructs a new, paused timer.
        """
        self.__offset = 0.0  # type: float
        self.__paused = True  # type: bool
        self.__time_start = 0.0  # type: float

    def stop(self) -> None:
        """
        Freezes the timer.
        """
        if not self.__paused:
            self.__offset += timer() - self.__time_start
            self.__paused = True

    def start(self) -> None:
        """
        Resumes the timer.
        """
        if self.__paused:
            self.__time_start = timer()
            self.__paused = False
        else:
            warnings.warn("timer is already running")

    def reset(self) -> None:
        """
        Resets and freezes the timer.
        """
        self.__offset = 0.0
        self.__paused = True

    @property
    def paused(self) -> bool:
        """
        Returns True if this stopwatch is paused, or False if not.
        """
        return self.__paused

    @property
    def duration(self) -> float:
        """
        The number of seconds that the stopwatch has been running.
        """
        d = self.__offset
        if not self.__paused:
            d += timer() - self.__time_start
        return d
