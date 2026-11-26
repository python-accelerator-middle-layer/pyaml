"""Named insertion-device control-variable configuration."""

from ..common.exception import PyAMLConfigException
from ..validation import DynamicValidation, register_schema

PYAMLCLASS = "ControlVariable"


@register_schema
class ControlVariable(DynamicValidation):
    """Configure one scalar coordinate without registering an accelerator element.

    ``backend`` and optional boolean ``movement_flag`` are opaque references
    resolved by the control-system backend. ``unit`` is the coordinate unit.
    """

    def __init__(self, name: str, unit: str, backend: str | None = None, movement_flag: str | None = None):
        if not name.strip() or not unit.strip():
            raise PyAMLConfigException("Each control variable requires a name and unit")
        for field, value in (("backend", backend), ("movement_flag", movement_flag)):
            if value is not None and not value.strip():
                raise PyAMLConfigException(f"{name}: {field} must not be empty")
        self.name = name
        self.unit = unit
        self.backend = backend
        self.movement_flag = movement_flag
