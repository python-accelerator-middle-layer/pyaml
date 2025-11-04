class PyAMLException(Exception):
    """Exception raised for PyAML error scenarios.

    Attributes:
        message -- explanation of the error
    """
    def __init__(self, message):
        super().__init__(message)
        self.message = message


class PyAMLConfigException(Exception):
    """Exception raised for PyAML configuration error scenarios.

    Attributes:
        message -- explanation of the error
    """
    def __init__(self, message):
        super().__init__(message)
        self.message = message
