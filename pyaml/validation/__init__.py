"""
PyAML validation subpackage.
"""

from .generator import SchemaGenerator
from .models import ConfigurationSchema
from .registry import SchemaRegistry, register_schema
from .validator import SchemaValidator

__all__ = [
    "ConfigurationSchema",
    "SchemaRegistry",
    "SchemaGenerator",
    "SchemaValidator",
    "register_schema",
]


# def __getattr__(name: str):
#     if name == "SchemaValidator":
#         from .validator import SchemaValidator

#         return SchemaValidator
#     raise AttributeError(name)
