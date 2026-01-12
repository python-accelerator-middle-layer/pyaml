import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict

from ..common.element import __pyaml_repr__
from ..control.deviceaccess import DeviceAccess

# Define the main class name for this module
PYAMLCLASS = "BPMArrayModel"

# TODO: Handle tilt and offset


class ConfigModel(BaseModel):
    """
    Configuration model for BPM array

    Parameters
    ----------
    pos : DeviceAccess, optional
        Orbit device name
    h_index : int, optional
        Index in the array
    v_index : int, optional
        Index in the array
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    pos: DeviceAccess | None
    h_index: int = 0
    v_index: int = 0


class BPMArrayModel:
    """
    Class that map an orbit device to individual BPM
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg

    def get_pos_device(self) -> DeviceAccess | None:
        """
        Get device handle used for position reading

        Returns
        -------
        DeviceAccess
            Orbit DeviceAcess
        """
        return self._cfg.pos

    def get_h_index(self) -> int:
        return self._cfg.h_index

    def get_v_index(self) -> int:
        return self._cfg.v_index

    def __repr__(self):
        return __pyaml_repr__(self)
