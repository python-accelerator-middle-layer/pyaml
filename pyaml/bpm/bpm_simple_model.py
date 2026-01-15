import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict

from pyaml.bpm.bpm_model import BPMModel

from ..common.element import __pyaml_repr__
from ..control.deviceaccess import DeviceAccess

# Define the main class name for this module
PYAMLCLASS = "BPMSimpleModel"


class ConfigModel(BaseModel):
    """
    Configuration model for BPM simple model

    Parameters
    ----------
    x_pos : DeviceAccess, optional
        Horizontal position device
    y_pos : DeviceAccess, optional
        Vertical position device
    x_pos_index : int, optional
        Index in the array when specified, otherwise scalar
        value is expected
    y_pos_index : int, optional
        Index in the array when specified, otherwise scalar
        value is expected
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    x_pos: DeviceAccess | None
    y_pos: DeviceAccess | None
    x_pos_index: int | None = None
    y_pos_index: int | None = None


class BPMSimpleModel(BPMModel):
    """
    Concrete implementation of BPMModel that simulates a BPM with tilt and
    offset values.
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        self.__x_pos = cfg.x_pos
        self.__y_pos = cfg.y_pos

    def get_pos_devices(self) -> list[DeviceAccess | None]:
        """
        Get device handles used for position reading

        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAcess
        """
        return [self.__x_pos, self.__y_pos]

    def get_tilt_device(self) -> DeviceAccess | None:
        """
        Get device handle used for tilt access

        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAcess
        """
        return None

    def get_offset_devices(self) -> list[DeviceAccess | None]:
        """
        Get device handles used for offset access

        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAcess
        """
        return [None, None]

    def x_pos_index(self) -> int | None:
        """
        Returns the index of the horizontal position in
        an array, otherwise a scalar value is expected from the
        corresponding DeviceAccess

        Returns
        -------
        int
            Index in the array, None for a scalar value
        """
        return self._cfg.x_pos_index

    def y_pos_index(self) -> int | None:
        """
        Returns the index of the veritcal position in
        an array, otherwise a scalar value is expected from the
        corresponding DeviceAccess

        Returns
        -------
        int
            Index in the array, None for a scalar value
        """
        return self._cfg.y_pos_index

    def __repr__(self):
        return __pyaml_repr__(self)
