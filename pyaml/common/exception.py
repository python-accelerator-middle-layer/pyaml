"""Exception types used to report PyAML and configuration failures."""


class PyAMLException(Exception):
    """
    Base exception for errors raised by PyAML runtime components.

    Parameters
    ----------
    message : object
        Error description retained on the exception as ``message``.
    """

    def __init__(self, message):
        """
        Initialize a PyAML runtime exception.
        """
        super().__init__(message)
        self.message = message


class PyAMLConfigException(Exception):
    """
    Exception raised when configuration cannot be loaded or validated.

    Parameters
    ----------
    message : object
        Error description retained on the exception as ``message``.
    """

    def __init__(self, message):
        """
        Initialize a configuration exception.
        """
        super().__init__(message)
        self.message = message
