"""Provides transformation schemas for classic GenProg-style statement operators."""
__all__ = (
    "AppendStatement",
    "DeleteStatement",
    "PrependStatement",
    "ReplaceStatement",
)

from darjeeling.transformation.classic.append import AppendStatement
from darjeeling.transformation.classic.delete import DeleteStatement
from darjeeling.transformation.classic.prepend import PrependStatement
from darjeeling.transformation.classic.replace import ReplaceStatement
