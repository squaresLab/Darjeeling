# -*- coding: utf-8 -*-
__all__ = ('DarjeelingEventProducer',)

import abc

from .event import DarjeelingEvent
from .handler import DarjeelingEventHandler


class DarjeelingEventProducer(abc.ABC):
    """Objects that implement this interface may produce Darjeeling events."""
    def dispatch(self, event: DarjeelingEvent) -> None:
        """Dispatches an event to all handlers attached to this producer."""
        for handler in self.handlers:
            handler.notify(event)

    @property
    @abc.abstractmethod
    def handlers(self) -> Iterator[DarjeelingEventHandler]:
        """Returns an iterator over the handlers attached to this object."""
        ...

    @abc.abstractmethod
    def attach_handler(self, handler: DarjeelingEventHandler) -> None:
        """Attaches an event handler to this object."""
        ...

    @abc.abstractmethod
    def remove_handler(self, handler: DarjeelingEventHandler) -> None:
        """Removes an event handler from this object."""
        ...
