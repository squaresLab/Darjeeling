import logging

from .version import __version__
from .problem import Problem
import darjeeling.exceptions

logging.getLogger(__name__).setLevel(logging.INFO)
logging.getLogger(__name__).addHandler(logging.NullHandler())
