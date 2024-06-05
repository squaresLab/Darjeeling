__all__ = ("EventEchoer",)

from .event import DarjeelingEvent
from .handler import DarjeelingEventHandler


class EventEchoer(DarjeelingEventHandler):
    """Prints a summary of all events to the stdout.
    Intended to be used for debugging and testing purposes.
    """
    def notify(self, event: DarjeelingEvent) -> None:
        print(str(event))
