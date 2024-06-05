__all__ = ("DarjeelingEventProducer",)

from collections.abc import Iterator
from typing import Any

from loguru import logger

from .event import DarjeelingEvent
from .handler import DarjeelingEventHandler


class DarjeelingEventProducer:
    """Objects that implement this interface may produce Darjeeling events."""
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.__handlers: list[DarjeelingEventHandler] = []

    def dispatch(self, event: DarjeelingEvent) -> None:
        """Dispatches an event to all handlers attached to this producer."""
        for handler in self.handlers:
            handler.notify(event)

    @property
    def handlers(self) -> Iterator[DarjeelingEventHandler]:
        """Returns an iterator over the handlers attached to this object."""
        yield from self.__handlers

    def attach_handler(self, handler: DarjeelingEventHandler) -> None:
        """Attaches an event handler to this object."""
        logger.debug(f"attaching event handler [{handler}] "
                     f"to producer [{self}]")
        if handler not in self.__handlers:
            self.__handlers.append(handler)
            logger.debug(f"attached event handler [{handler}] "
                         f"to producer [{self}]")
        else:
            logger.debug(f"event handler [{handler}] already attached "
                         f"to producer [{self}]")

    def remove_handler(self, handler: DarjeelingEventHandler) -> None:
        """Removes an event handler from this object."""
        logger.debug(f"removing event handler [{handler}] "
                     f"from producer [{self}]")
        if handler not in self.__handlers:
            logger.warning(f"handler [{handler}] not attached "
                           f"to producer [{self}]")
        self.__handlers.remove(handler)
        logger.debug(f"removed event handler [{handler}] "
                     f"from producer [{self}]")
