# -*- coding: utf-8 -*-
from .searcher import Searcher


class Session:
    """Used to manage and inspect an interactive repair session."""
    def pause() -> None:
        """Pauses the session."""
        raise NotImplementedError
