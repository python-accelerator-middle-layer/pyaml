"""Insertion-device elements."""

from ..validation import SchemaRegistry
from ..validation.schema_builder import generate_configuration_schema
from .insertion_device import PYAMLCLASS, InsertionDevice

__all__ = ["InsertionDevice"]

SchemaRegistry().register(f"{__name__}.InsertionDevice", generate_configuration_schema(InsertionDevice))
