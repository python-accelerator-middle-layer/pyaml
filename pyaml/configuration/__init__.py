"""
PyAML configuration subpackage.
"""

from .factory import Factory
from .fileloader import get_root_folder, set_root_folder
from .manager import ConfigurationManager, UnsupportedConfigurationRootError
from .validation import ConfigurationSchema, register_schema

__all__ = [
    "ConfigurationManager",
    "ConfigurationSchema",
    "UnsupportedConfigurationRootError",
    "Factory",
    "get_root_folder",
    "set_root_folder",
    "register_schema",
]


def __getattr__(name: str):
    if name == "SchemaValidator":
        from .validation import SchemaValidator

        return SchemaValidator
    raise AttributeError(name)
