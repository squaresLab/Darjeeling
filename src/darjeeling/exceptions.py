class DarjeelingError(Exception):
    pass


class NoFailingTests(DarjeelingError):
    pass


class NoImplicatedLines(DarjeelingError):
    pass
