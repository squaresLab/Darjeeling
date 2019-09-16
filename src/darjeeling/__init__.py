import logging

from . import exceptions
from .version import __version__
from .problem import Problem

logging.getLogger(__name__).setLevel(logging.INFO)
logging.getLogger(__name__).addHandler(logging.NullHandler())
