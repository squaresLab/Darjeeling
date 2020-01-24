# -*- coding: utf-8 -*-
from loguru import logger as _logger
_logger.disable('darjeeling')

from . import exceptions
from .container import ProgramContainer
from .version import __version__
from .environment import Environment
from .problem import Problem
from .events import (DarjeelingEvent, DarjeelingEventHandler,
                     DarjeelingEventProducer)

# this must come at the end to prevent circular imports
from . import plugins
