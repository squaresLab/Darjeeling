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


class UnknownTransformationSchemaException(DarjeelingError):
    """
    A given transformation uses a schema that does not exist or has not been
    registered.
    """
    def __init__(self, name: str) -> None:
        msg = "unknown transformation schema: {}".format(name)
        super().__init__(msg)
