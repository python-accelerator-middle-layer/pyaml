from typing import Union
from pyaml.exception import PyAMLException


class PyAMLConfigException(PyAMLException):
    """Exception raised for custom error scenarios.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, config_key = None, parent_exception:Exception = None):
        self.parent_keys = []
        self.config_key = config_key
        self.parent_exception = parent_exception
        message = "An exception occurred while building object."
        if parent_exception is not None:
            if isinstance(parent_exception, PyAMLConfigException) and parent_exception.config_key is not None:
                self.parent_keys.append(parent_exception.config_key)
                self.parent_keys.extend(parent_exception.parent_keys)
                if config_key is not None:
                    message = f"An exception occurred while building key '{config_key}.{parent_exception.get_keys()}': {parent_exception.get_original_message()}"
                else:
                    message = f"An exception occurred while building object in '{parent_exception.get_keys()}': {parent_exception.get_original_message()}"
            else:
                if isinstance(parent_exception, PyAMLException):
                    parent_message = parent_exception.message
                else:
                    parent_message = str(parent_exception)
                if config_key is not None:
                    message = f"An exception occurred while building key '{config_key}': {parent_message}"
                else:
                    message = f"An exception occurred while building object: {parent_message}"
        super().__init__(message)

    def get_keys(self) -> str:
        keys = ""
        if self.config_key is not None:
            if len(self.parent_keys)>0:
                keys = ".".join(self.parent_keys)
                keys += "."
            keys += self.config_key
        return keys

    def get_original_message(self):
        if self.parent_exception is not None:
            if isinstance(self.parent_exception, PyAMLConfigException):
                return self.parent_exception.get_original_message()
            elif isinstance(self.parent_exception, PyAMLException):
                return self.parent_exception.message
            else:
                return str(self.parent_exception)
        else:
            return self.message