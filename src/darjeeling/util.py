# -*- coding: utf-8 -*-
import warnings
import inspect
import logging
from typing import List, Union, Tuple, ClassVar, Dict, Type, Set
from timeit import default_timer as timer

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)


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


class DynamicallyRegistered:
    """Provides dynamic registration and lookup of classes to a base class."""
    NAME: ClassVar[str]
    _registration_type_name: ClassVar[str]
    _registry: ClassVar[Dict[str, Type]]
    _registered_class_names: ClassVar[Set[str]]

    @classmethod
    def lookup(cls, name: str):
        # TODO should only be exposed by the base type
        return cls._registry[name]

    def __init_subclass__(cls, *args, **kwargs) -> None:
        full_class_name = cls.__qualname__
        has_name = hasattr(cls, 'NAME')
        is_root_type = not hasattr(cls, '_registration_type_name')
        is_abstract = inspect.isabstract(cls)

        if is_root_type and has_name or is_abstract:
            msg = f'Illegal "NAME" attribute in abstract or root class: {cls}'
            raise TypeError(msg)

        if is_root_type:
            cls._registration_type_name = cls.__name__
            cls._registry = {}
            cls._registered_class_names = set()
            logger.debug("enabled dynamic registration for %s", cls)
            return

        if is_abstract:
            return

        if not has_name:
            msg = f"Missing attribute 'NAME' in class definition: {cls}"
            raise TypeError(msg)

        # The use of class decorators may cause __init_subclass__ to be called
        # several times for a given class. To avoid unexpected behaviour, we
        # keep track of the names of the classes that have been registered, and
        # we check whether a given class has been registered on the basis of
        # its name. Note that we _must_ update the registration to point to the
        # new class (since it's a different object).
        name: str = cls.NAME
        name_is_registered = name in cls._registry
        class_is_registered = full_class_name in cls._registered_class_names
        if name_is_registered and not class_is_registered:
            msg = f"Class already registered under given name [{name}]: {cls}"
            raise TypeError(msg)

        cls._registry[name] = cls

        if class_is_registered:
            logger.debug("updated [%s] registration for decorated class: %s",
                         cls._registration_type_name, cls)
        else:
            logger.debug("added [%s] registration for class: %s",
                         cls._registration_type_name, cls)
            cls._registered_class_names.add(full_class_name)


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
