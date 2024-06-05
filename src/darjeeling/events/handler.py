__all__ = ("DarjeelingEventHandler",)

import abc

from .event import DarjeelingEvent


class DarjeelingEventHandler(abc.ABC):
    """Provides an interface for handling Darjeeling events."""
    @abc.abstractmethod
    def notify(self, event: DarjeelingEvent) -> None:
        """Notifies this event handler of an event."""
        ...
