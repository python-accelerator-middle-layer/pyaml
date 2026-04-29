from pyaml.common.exception import PyAMLException

from .attribute import Attribute, ConfigModel

PYAMLCLASS: str = "AttributeReadOnly"


class AttributeReadOnly(Attribute):
    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg)

    def set(self, value):
        raise PyAMLException(f"Tango attribute {self._cfg.attribute} is not writable.")

    def set_and_wait(self, value):
        raise PyAMLException(f"Tango attribute {self._cfg.attribute} is not writable.")

    def get(self):
        return self.readback().value
