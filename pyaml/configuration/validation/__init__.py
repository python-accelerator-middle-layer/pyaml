"""
PyAML validation subpackage.
"""

from .models import ConfigurationSchema
from .registry import SchemaRegistry, register_schema

__all__ = [
    "ConfigurationSchema",
    "SchemaRegistry",
    "register_schema",
]


def __getattr__(name: str):
    if name == "SchemaValidator":
        from .validator import SchemaValidator

        return SchemaValidator
    raise AttributeError(name)
