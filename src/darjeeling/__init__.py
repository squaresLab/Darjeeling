from loguru import logger as _logger

_logger.disable("darjeeling")

# this must come at the end to prevent circular imports
import darjeeling.container
import darjeeling.environment
import darjeeling.events
import darjeeling.exceptions
import darjeeling.plugins
import darjeeling.problem
from darjeeling.version import __version__

import darjeeling.transformation.classic
import darjeeling.transformation.line
