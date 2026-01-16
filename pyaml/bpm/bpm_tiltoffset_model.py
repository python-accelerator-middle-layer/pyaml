import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict

from pyaml.bpm.bpm_model import BPMModel
from pyaml.bpm.bpm_simple_model import BPMSimpleModel

from ..common.element import __pyaml_repr__
from ..control.deviceaccess import DeviceAccess

# Define the main class name for this module
PYAMLCLASS = "BPMTiltOffsetModel"

# TODO: Implepement indexed offset and tilt


class ConfigModel(BaseModel):
    """
    Configuration model for BPM with tilt and offset

    Parameters
    ----------
    x_pos : DeviceAccess, optional
        Horizontal position device
    y_pos : DeviceAccess, optional
        Vertical position device
    x_offset : DeviceAccess, optional
        Horizontal BPM offset device
    y_offset : DeviceAccess, optional
        Vertical BPM offset device
    tilt : DeviceAccess, optional
        BPM tilt device
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    x_pos: DeviceAccess | None
    y_pos: DeviceAccess | None
    x_pos_index: int | None = None
    y_pos_index: int | None = None
    x_offset: DeviceAccess | None
    y_offset: DeviceAccess | None
    tilt: DeviceAccess | None


class BPMTiltOffsetModel(BPMSimpleModel):
    """
    Concrete implementation of BPMModel that simulates a BPM with tilt and
    offset values.
    """

    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg)
        self.__x_pos = cfg.x_pos
        self.__y_pos = cfg.y_pos
        self.__x_offset = cfg.x_offset
        self.__y_offset = cfg.y_offset
        self.__tilt = cfg.tilt

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
        DeviceAccess
            DeviceAcess
        """
        return self.__tilt

    def get_offset_devices(self) -> list[DeviceAccess | None]:
        """
        Get device handles used for offset access

        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAcess
        """
        return [self.__x_offset, self.__y_offset]

    def __repr__(self):
        return __pyaml_repr__(self)
