# -*- coding: utf-8 -*-
import attr as _attr


class DarjeelingError(Exception):
    """Base class used by all Darjeeling exceptions."""


class LanguageNotSupported(DarjeelingError):
    """Darjeeling does not support the given language."""
    def __init__(self, name: str) -> None:
        msg = "language not supported: {}".format(name)
        super().__init__(msg)


class SearchAlreadyStarted(DarjeelingError):
    """The searcher has already begun searching for patches."""


@_attr.s(auto_exc=True, auto_attribs=True)
class FileNotFound(DarjeelingError):
    """A given file could not be found."""
    filename: str


class TimeLimitReached(DarjeelingError):
    """The search has halted after reaching its time limit."""


class CandidateLimitReached(DarjeelingError):
    """The search has halted after reaching its candidate limit."""


class SearchExhausted(DarjeelingError):
    """The search has evaluated all of its candidate patches."""


class NoFailingTests(DarjeelingError):
    """
    The program under repair has no failing tests and therefore does not
    constitute a valid test-based repair problem.
    """


class NoImplicatedLines(DarjeelingError):
    """
    The program under repair has no lines that have been marked as suspicious
    by its fault localisation and coverage information.
    """


class BuildFailure(DarjeelingError):
    """The project failed to build."""


class NameInUseException(DarjeelingError):
    """A given name is already in use by another resource."""


class UnknownTransformationSchemaException(DarjeelingError):
    """
    A given transformation uses a schema that does not exist or has not been
    registered.
    """
    def __init__(self, name: str) -> None:
        msg = "unknown transformation schema: {}".format(name)
        super().__init__(msg)


class BadConfigurationException(DarjeelingError):
    """An illegal configuration file was provided to Darjeeling."""
    def __init__(self, reason: str) -> None:
        msg = "bad configuration file: {}".format(reason)
        super().__init__(msg)
