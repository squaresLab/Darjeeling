# -*- coding: utf-8 -*-
import warnings
import inspect
import logging
from typing import List, Union, Tuple, ClassVar, Dict, Type, Set, Iterator, Optional
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


def dynamically_registered(cls,
                           *,
                           length: Optional[str] = '__len__',
                           iterator: Optional[str] = '__iter__',
                           lookup: Optional[str] = 'lookup',
                           register_on: str = 'NAME'
                           ):
    logger.debug("Adding dynamic registration to class: %s", cls)
    logger.debug("Registered via attribute: %s", register_on)

    registry = {}
    registered_class_names = set()

    def method_hook_subclass(subcls, *args, **kwargs) -> None:
        has_name = hasattr(subcls, register_on)
        is_abstract = inspect.isabstract(subcls)
        if has_name and is_abstract:
            msg = f'Illegal "NAME" attribute in abstract class: {subcls}'
            raise TypeError(msg)
        if is_abstract:
            return
        if not has_name:
            msg = f"Missing attribute '{register_on}' in class definition: {subcls}"
            raise TypeError(msg)

        # The use of class decorators may cause __init_subclass__ to be called
        # several times for a given class. To avoid unexpected behaviour, we
        # keep track of the names of the classes that have been registered, and
        # we check whether a given class has been registered on the basis of
        # its name. Note that we _must_ update the registration to point to the
        # new class (since it's a different object).
        name: str = getattr(subcls, register_on)
        name_is_registered = name in registry
        subcls_is_registered = subcls.__qualname__ in registered_class_names
        if name_is_registered and not subcls_is_registered:
            msg = f"Class already registered as '{name}': {subcls}"
            raise TypeError(msg)

        registry[name] = subcls

        if subcls_is_registered:
            logger.debug("updated [%s] registration for decorated class: %s",
                         cls.__name__, subcls)
        else:
            logger.debug("added [%s] registration for class: %s",
                         cls.__name__, subcls)
            registered_class_names.add(subcls.__qualname__)

    def method_length() -> int:
        return len(cls._registry)

    def method_iterator() -> Iterator[str]:
        yield from cls._registry

    def method_lookup(name: str):
        return cls._registry[name]

    if length:
        logger.debug("Adding length method [%s] to class [%s]", length, cls)
        setattr(cls, length, staticmethod(method_length))
    if False: # FIXME iterator:
        logger.debug("Adding iterator method [%s] to class [%s]",
                     iterator, cls)
        setattr(cls, iterator, staticmethod(method_iterator))
    if lookup:
        logger.debug("Adding lookup method [%s] to class [%s]", lookup, cls)
        setattr(cls, lookup, staticmethod(method_lookup))

    setattr(cls, '__init_subclass__', classmethod(method_hook_subclass))

    logger.debug("Added dynamic registration to class: %s", cls)
    return cls


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
