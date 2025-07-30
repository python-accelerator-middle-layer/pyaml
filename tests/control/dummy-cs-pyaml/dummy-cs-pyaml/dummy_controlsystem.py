from pydantic import BaseModel
from pyaml.control.controlsystem import ControlSystem

PYAMLCLASS = "DummyControlSystem"

class ConfigModel(BaseModel):
    """
    Configuration model for a Tango Control System.

    Attributes
    ----------
    name : str
        Name of the control system.
    """
    name: str

class DummyControlSystem(ControlSystem):

    def __init__(self, cfg: ConfigModel):
        super().__init__()
        self._cfg = cfg


    def init_cs(self):
        pass


    def name(self) -> str:
        """
        Return the name of the control system.

        Returns
        -------
        str
            Name of the control system.
        """
        return self._cfg.name
