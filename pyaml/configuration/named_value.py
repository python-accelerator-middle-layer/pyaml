"""Reusable named values for object-based configuration."""

from typing import Any

from ..common.exception import PyAMLConfigException
from ..validation import DynamicValidation, register_schema

PYAMLCLASS = "NamedValue"


@register_schema
class NamedValue(DynamicValidation):
    """Associate a nonempty name with a value without registering an element.

    The consuming class validates value types, allowed names and uniqueness.
    Values are not coerced to a common scalar type.

    Configuration
    -------------
    .. code-block:: yaml

        - type: pyaml.configuration.named_value
          name: gap
          value: 4.0
    """

    def __init__(self, name: str, value: Any):
        if not name.strip():
            raise PyAMLConfigException("NamedValue requires a nonempty name")
        self.name = name
        self.value = value
