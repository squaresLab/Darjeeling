class DarjeelingError(Exception):
    """
    Base class used by all Darjeeling exceptions.
    """


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
    """
    The project failed to build.
    """


class NameInUseException(DarjeelingError):
    """
    A given name is already in use by another resource.
    """
