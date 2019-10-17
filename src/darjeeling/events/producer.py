# -*- coding: utf-8 -*-
__all__ = ('DarjeelingEventProducer',)

from typing import Iterator, List, Any
import logging

import abc

from .event import DarjeelingEvent
from .handler import DarjeelingEventHandler

logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class DarjeelingEventProducer:
    """Objects that implement this interface may produce Darjeeling events."""
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)  # type: ignore # mypy issue 4335
        self.__handlers: List[DarjeelingEventHandler] = []

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
        logger.debug("attaching event handler [%s] to producer [%s]",
                     handler, self)
        if not handler in self.__handlers:
            self.__handlers.append(handler)
            logger.debug("attached event handler [%s] to producer [%s]",
                         handler, self)
        else:
            logger.debug("event handler [%s] already attached to"
                         " producer [%s]",
                         handler, self)

    def remove_handler(self, handler: DarjeelingEventHandler) -> None:
        """Removes an event handler from this object."""
        logger.debug("removing event handler [%s] from producer [%s]",
                     handler, self)
        if not handler in self.__handlers:
            m = f"handler [{handler}] not attached to producer [{self}]"
            logger.warning(m)
        self.__handlers.remove(handler)
        logger.debug("removed event handler [%s] from producer [%s]",
                     handler, self)
