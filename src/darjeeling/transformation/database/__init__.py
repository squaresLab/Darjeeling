"""Provides a common interface for interacting with transformation databases.

Transformation databases are a convenient abstraction for storing and querying
transformations to a given program. This module defines a common interface for
all interacting with transformation databases as well as reference
implementations of that interface. Developers may extend Darjeeling to add their
own, customized transformation database implementation.
"""
__all__ = ("TransformationDatabase",)

from darjeeling.transformation.database.base import TransformationDatabase
