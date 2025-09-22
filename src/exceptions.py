"""Feeder specific exceptions."""


class AbortProcedureError(Exception):
    """Exception raised when the procedure must be aborted."""

    def __init__(self, message: str, *args):
        self.message = message
        super().__init__(message, *args)


class InvalidYamlError(Exception):
    def __init__(self, message: str, *args, **kwargs):
        self.message = message
        super().__init__(message, *args)
