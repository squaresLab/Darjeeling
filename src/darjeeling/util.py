# -*- coding: utf-8 -*-
import warnings
import inspect
from types import TracebackType
from typing import (
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)
from timeit import default_timer as timer

from loguru import logger


def tuple_from_iterable(val: Iterable[Any]) -> Tuple[Any, ...]:
    """Builds a tuple from an iterable.
    Workaround for https://github.com/python-attrs/attrs/issues/519
    """
    return tuple(val)


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


def _dynamically_registered(cls,
                            *,
                            length: Optional[str] = '__len__',
                            iterator: Optional[str] = '__iter__',
                            lookup: Optional[str] = 'lookup',
                            register_on: str = 'NAME'
                            ):
    logger.debug(f"Adding dynamic registration to class: {cls}")
    logger.debug(f"Registered via attribute: {register_on}")

    registry: Dict[str, Any] = {}
    registered_class_names: Set[str] = set()

    def method_hook_subclass(subcls, *args, **kwargs) -> None:
        has_name = hasattr(subcls, register_on)
        is_abstract = inspect.isabstract(subcls)
        if has_name and is_abstract:
            msg = f'Illegal "{register_on}" attribute in abstract class: {subcls}'
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
            logger.debug(f"updated [{cls.__name__}] registration for "
                         f"decorated class: {subcls}")
        else:
            logger.debug(f"added [{cls.__name__}] registration for "
                         f"class: {subcls}")
            registered_class_names.add(subcls.__qualname__)

    def method_length() -> int:
        return len(registry)

    def method_iterator() -> Iterator[str]:
        yield from registry

    def method_lookup(name: str):
        return registry[name]

    if length:
        logger.debug(f"Adding length method [{length}] to class [{cls}]")
        setattr(cls, length, staticmethod(method_length))
    if iterator:
        logger.debug(f"Adding iterator method [{iterator}] to class [{cls}]")
        setattr(cls, iterator, staticmethod(method_iterator))
    if lookup:
        logger.debug(f"Adding lookup method [{lookup}] to class [{cls}]")
        setattr(cls, lookup, staticmethod(method_lookup))

    setattr(cls, '__init_subclass__', classmethod(method_hook_subclass))

    logger.debug(f"Added dynamic registration to class: {cls}")
    return cls


def dynamically_registered(register_on: str = 'NAME',
                           *,
                           length: Optional[str] = '__len__',
                           iterator: Optional[str] = '__iter__',
                           lookup: Optional[str] = 'lookup',
                           ):
    def decorator(cls):
        return _dynamically_registered(cls,
                                       register_on=register_on,
                                       length=length,
                                       iterator=iterator,
                                       lookup=lookup)

    return decorator


class Stopwatch:
    def __init__(self) -> None:
        """Constructs a new, paused timer."""
        self.__offset: float = 0.0
        self.__paused: bool = True
        self.__time_start: float = 0.0

    def __enter__(self) -> 'Stopwatch':
        self.start()
        return self

    def __exit__(
        self,
        ex_type: Optional[Type[BaseException]],
        ex_val: Optional[BaseException],
        ex_tb: Optional[TracebackType],
    ) -> None:
        self.stop()

    def stop(self) -> None:
        """Freezes the timer."""
        if not self.__paused:
            self.__offset += timer() - self.__time_start
            self.__paused = True

    def start(self) -> None:
        """Resumes the timer."""
        if self.__paused:
            self.__time_start = timer()
            self.__paused = False
        else:
            warnings.warn("timer is already running")

    def reset(self) -> None:
        """Resets and freezes the timer."""
        self.__offset = 0.0
        self.__paused = True

    @property
    def paused(self) -> bool:
        """Returns True if this stopwatch is paused, or False if not."""
        return self.__paused

    @property
    def duration(self) -> float:
        """The number of seconds that the stopwatch has been running."""
        d = self.__offset
        if not self.__paused:
            d += timer() - self.__time_start
        return d
