import typing as _typing

import attr as _attr

if _typing.TYPE_CHECKING:
    from .build_instructions import BuildStep
    from .candidate import Candidate


class DarjeelingError(Exception):
    """Base class used by all Darjeeling exceptions."""


class UnableToObtainIpAddress(DarjeelingError):
    """Failed to obtain the IP address of a container."""


class LanguageNotSupported(DarjeelingError):
    """Darjeeling does not support the given language."""
    def __init__(self, name: str) -> None:
        msg = f"language not supported: {name}"
        super().__init__(msg)


class SearchAlreadyStarted(DarjeelingError):
    """The searcher has already begun searching for patches."""


@_attr.s(auto_exc=True, auto_attribs=True)
class FileNotFound(DarjeelingError):
    """A given file could not be found."""
    filename: str


@_attr.s(auto_exc=True, auto_attribs=True)
class BuildStepFailed(DarjeelingError):
    """A step in the build process failed."""
    step: "BuildStep"
    returncode: int
    duration: float
    output: _typing.Optional[str]


class FailedToApplyPatch(DarjeelingError):
    """Failed to apply a patch to the program."""


class TimeLimitReached(DarjeelingError):
    """The search has halted after reaching its time limit."""


class TestLimitReached(DarjeelingError):
    """The search has halted after reaching its test limit."""


class CandidateLimitReached(DarjeelingError):
    """The search has halted after reaching its candidate limit."""


@_attr.s(auto_exc=True, auto_attribs=True)
class UnexpectedCandidateEvaluationError(DarjeelingError):
    """An unexpected error occurred when evaluating a candidate patch."""
    candidate: "Candidate"
    error: Exception


class SearchExhausted(DarjeelingError):
    """The search has evaluated all of its candidate patches."""


class NoFailingTests(DarjeelingError):
    """The program under repair has no failing tests and therefore does not
    constitute a valid test-based repair problem.
    """


class NoImplicatedLines(DarjeelingError):
    """The program under repair has no lines that have been marked as suspicious
    by its fault localisation and coverage information.
    """


class BuildFailure(DarjeelingError):
    """The project failed to build."""


class NameInUseException(DarjeelingError):
    """A given name is already in use by another resource."""


class UnknownTransformationSchemaException(DarjeelingError):
    """A given transformation uses a schema that does not exist or has not been
    registered.
    """
    def __init__(self, name: str) -> None:
        msg = f"unknown transformation schema: {name}"
        super().__init__(msg)


class BadConfigurationException(DarjeelingError):
    """An illegal configuration file was provided to Darjeeling."""
    def __init__(self, reason: str) -> None:
        msg = f"bad configuration file: {reason}"
        super().__init__(msg)
