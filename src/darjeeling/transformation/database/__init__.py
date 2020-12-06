# -*- coding: utf-8 -*-
"""
Transformation databases are a convenient abstraction for storing and querying
transformations to a given program. This module defines a common interface for
all interacting with transformation databases as well as reference
implementations of that interface. Developers may extend Darjeeling to add their
own, customized transformation database implementation.
"""
from .base import TransformationDatabase
