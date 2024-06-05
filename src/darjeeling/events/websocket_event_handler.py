__all__ = ("WebSocketEventHandler",)

import asyncio
import json
import queue
import threading
import typing

import attr
import websockets
import websockets.legacy.server

from .event import DarjeelingEvent
from .handler import DarjeelingEventHandler

if typing.TYPE_CHECKING:
    EventQueue = queue.Queue[DarjeelingEvent]
else:
    EventQueue = queue.Queue


@attr.s(eq=False, hash=False)
class WebSocketEventHandler(DarjeelingEventHandler):
    """Forwards all events to a WebSocket.

    Attributes
    ----------
    hostname: str
        The hostname of the websocket.
    port: int
        The port of the websocket.
    """
    hostname: str = attr.ib(default="127.0.0.1")
    port: int = attr.ib(default=8888)
    _server: websockets.legacy.server.Serve = \
        attr.ib(init=False, repr=False)
    _thread: threading.Thread = attr.ib(init=False, repr=False)
    _event_queue: EventQueue = attr.ib(init=False, repr=False)

    async def __serve(self, websocket, path):  # type: ignore
        # TODO WHILE OPEN
        while True:
            event = self._event_queue.get()
            message = json.dumps(event.to_dict())
            await websocket.send(message)

    def __attrs_post_init__(self) -> None:
        loop = asyncio.new_event_loop()
        self._event_queue = queue.Queue()
        self._server = \
            websockets.serve(self.__serve, self.hostname, self.port, loop=loop)  # type: ignore

        def loop_in_thread(loop: asyncio.AbstractEventLoop) -> None:
            loop.run_until_complete(self._server)
            loop.run_forever()

        self._thread = threading.Thread(target=loop_in_thread, daemon=True, args=(loop,))
        self._thread.start()

    def close(self) -> None:
        """Closes the WebSocket associated with this handler."""
        # TODO notify of closure via Event?
        self._server.ws_server.close()
        self._thread.join()
        # destroy event loop?

    def notify(self, event: DarjeelingEvent) -> None:
        self._event_queue.put(event)
