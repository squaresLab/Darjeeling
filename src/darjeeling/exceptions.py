class DarjeelingError(Exception):
    pass


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
