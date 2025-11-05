from pyaml.bpm.bpm_model import BPMModel
from pydantic import BaseModel,ConfigDict
import numpy as np
from ..control.deviceaccess import DeviceAccess
from ..common.element import __pyaml_repr__

from numpy.typing import NDArray
# Define the main class name for this module
PYAMLCLASS = "BPMSimpleModel"

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

    def read_position(self) -> NDArray:
        """
        Simulate reading the position values from a BPM.
        Returns
        -------
        np.ndarray
            Array of shape (2,) containing the horizontal and vertical
            positions
        """
        return np.array([self.__x_pos.get(), self.__y_pos.get()])
    
    def read_tilt(self) -> float:
        """
        Simulate reading the tilt value from a BPM.
        Returns
        -------
        float
            The tilt value of the BPM
        """
        raise NotImplementedError("Tilt reading not implemented in this model.")
    
    def read_offset(self) -> NDArray:
        """
        Simulate reading the offset values from a BPM.
        Returns
        -------
        np.ndarray
            Array of shape (2,) containing the horizontal and vertical
            offsets
        """
        raise NotImplementedError("Offset reading not implemented in this model.")
    def set_tilt(self, tilt: float):
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
    
    def set_offset(self, offset_values: np.ndarray):
        """
        Simulate setting the offset values of a BPM
        Parameters
        ----------
        offset_values : np.ndarray
            Array of shape (2,) containing the horizontal and vertical
            offsets to set for the BPM
        """
        raise NotImplementedError("Offset setting not implemented in this model.")
    
    def get_pos_devices(self) -> list[DeviceAccess]:
        """
        Get device handles used for position reading
        
        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAcess
        """
        return [self.__x_pos,self.__y_pos]

    def get_tilt_device(self) -> DeviceAccess:
        """
        Get device handle used for tilt access
        
        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAcess
        """
        return []

    def get_offset_devices(self) -> list[DeviceAccess]:
        """
        Get device handles used for offset access
        
        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAcess
        """
        return []

    def __repr__(self):
        return __pyaml_repr__(self)

