from pyaml.bpm.bpm_model import BPMModel
from pyaml.bpm.bpm_simple_model import BPMSimpleModel
from pydantic import BaseModel,ConfigDict
import numpy as np
from ..control.deviceaccess import DeviceAccess
from numpy.typing import NDArray
# Define the main class name for this module
PYAMLCLASS = "BPMTiltOffsetModel"

class ConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

    x_pos: DeviceAccess
    """Horizontal position"""
    y_pos: DeviceAccess
    """Vertical position"""
    x_offset: DeviceAccess
    """Horizontal BPM offset"""
    y_offset: DeviceAccess
    """Vertical BPM offset"""
    tilt: DeviceAccess
    """BPM tilt"""

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

    def read_hardware_tilt_value(self) -> float:
        """
        Simulate reading the tilt value from a BPM.
        Returns
        -------
        float
            The tilt value of the BPM
        """
        return self.__tilt.get()

    def read_hardware_offset_values(self) -> NDArray:
        """
        Simulate reading the offset values from a BPM.
        Returns
        -------
        np.ndarray
            Array of shape (2,) containing the horizontal and vertical
            offsets
        """
        return np.array([self.__x_offset.get(), self.__y_offset.get()])

    def set_hardware_tilt_value(self, tilt: float):
        """
        Simulate setting the tilt value of a BPM.
        Parameters
        ----------
        tilt : float
            The tilt value to set for the BPM
        Returns
        -------
        None
        """
        self.__tilt.set(tilt)

    def set_hardware_offset_values(self, offset_values: np.ndarray):
        """
        Simulate setting the offset values of a BPM
        Parameters
        ----------
        offset_values : np.ndarray
            Array of shape (2,) containing the horizontal and vertical
            offsets to set for the BPM
        """
        self.__x_offset.set(offset_values[0])
        self.__y_offset.set(offset_values[1])

