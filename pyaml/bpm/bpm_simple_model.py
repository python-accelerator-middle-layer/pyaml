from pyaml.bpm.bpm_model import BPMModel
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

class BPMSimpleModel(BPMModel):
    """
    Concrete implementation of BPMModel that simulates a BPM with tilt and
    offset values.
    """
    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg 
        
        self.__x_pos = cfg.x_pos
        self.__y_pos = cfg.y_pos

    def read_hardware_position_values(self) -> NDArray:
        """
        Simulate reading the position values from a BPM.
        Returns
        -------
        np.ndarray
            Array of shape (2,) containing the horizontal and vertical
            positions
        """
        return np.array([self.__x_pos.get(), self.__y_pos.get()])

    def read_hardware_tilt_value(self) -> float:
        """
        Simulate reading the tilt value from a BPM.
        Returns
        -------
        float
            The tilt value of the BPM
        """
        raise NotImplementedError("Tilt reading not implemented in this model.")

    def read_hardware_offset_values(self) -> NDArray:
        """
        Simulate reading the offset values from a BPM.
        Returns
        -------
        np.ndarray
            Array of shape (2,) containing the horizontal and vertical
            offsets
        """
        raise NotImplementedError("Offset reading not implemented in this model.")
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
        raise NotImplementedError("Tilt setting not implemented in this model.")

    def set_hardware_offset_values(self, offset_values: np.ndarray):
        """
        Simulate setting the offset values of a BPM
        Parameters
        ----------
        offset_values : np.ndarray
            Array of shape (2,) containing the horizontal and vertical
            offsets to set for the BPM
        """
        raise NotImplementedError("Offset setting not implemented in this model.")

