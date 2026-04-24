from pydantic import BaseModel, ConfigDict

from pyaml.bpm.bpm_model import BPMModel

from ..common.element import __pyaml_repr__

# Define the main class name for this module
PYAMLCLASS = "BPMSimpleModel"


class ConfigModel(BaseModel):
    """
    Configuration model for BPM simple model

    Parameters
    ----------
    x_pos : str
        Horizontal position catalog key
    y_pos : str
        Vertical position catalog key
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    x_pos: str
    y_pos: str


class BPMSimpleModel(BPMModel):
    """
    Concrete implementation of BPMModel that simulates a BPM with tilt and
    offset values.
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        self.__x_pos = cfg.x_pos
        self.__y_pos = cfg.y_pos

    def get_pos_devices(self) -> list[str]:
        """
        Get device handles used for position reading

        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAcess
        """
        return [self.__x_pos, self.__y_pos]

    def get_tilt_device(self) -> str | None:
        """
        Get device handle used for tilt access

        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAcess
        """
        return None

    def get_offset_devices(self) -> list[str | None]:
        """
        Get device handles used for offset access

        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAcess
        """
        return [None, None]

    def __repr__(self):
        return __pyaml_repr__(self)
