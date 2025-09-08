from pyaml.bpm.bpm_model import BPMModel
from pydantic import BaseModel,ConfigDict
import numpy as np
from ..control.deviceaccess import DeviceAccess

# Define the main class name for this module
PYAMLCLASS = "BPMTiltOffsetModel"

class ConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

    bpm_device: DeviceAccess
    """Power converter device to apply currrent"""
    position_unit: str
    """Unit of the positions (i.e. mm)"""
    tilt_unit: str
    """Unit of the tilt (i.e. rad)"""
    offset_unit: str
    """Unit of the offsets (i.e. mm)"""

class BPMTiltOffsetModel(BPMModel):
    """
    Concrete implementation of BPMModel that simulates a BPM with tilt and
    offset values.
    """
    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg 
        
        self.__position_unit = cfg.position_unit
        self.__tilt_unit = cfg.tilt_unit
        self.__offset_unit = cfg.offset_unit
        self.__position_hardware_unit = cfg.bpm_device.unit()
        self.__bpm_device = cfg.bpm_device

    def read_hardware_position_values(self) -> np.ndarray:
        """
        Simulate reading the position values from a BPM.
        Returns
        -------
        np.ndarray
            Array of shape (2,) containing the horizontal and vertical
            positions
        """
        return self.__bpm_device.get_position()

    def set_hardware_position_values(self, position_values: np.ndarray):
        """
        Simulate setting the position values of a BPM
        Parameters
        ----------
        position_values : np.ndarray
            Array of shape (2,) containing the horizontal and vertical
            positions to set for the BPM
        """
        self.__bpm_device.set_position(position_values)

    def read_hardware_tilt_value(self) -> float:
        """
        Simulate reading the tilt value from a BPM.
        Returns
        -------
        float
            The tilt value of the BPM
        """
        return self.__bpm_device.get_tilt()

    def read_hardware_offset_values(self) -> np.ndarray:
        """
        Simulate reading the offset values from a BPM.
        Returns
        -------
        np.ndarray
            Array of shape (2,) containing the horizontal and vertical
            offsets
        """
        return self.__bpm_device.get_offset()

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
        self.__bpm_device.set_tilt(tilt)

    def set_hardware_offset_values(self, offset_values: np.ndarray):
        """
        Simulate setting the offset values of a BPM
        Parameters
        ----------
        offset_values : np.ndarray
            Array of shape (2,) containing the horizontal and vertical
            offsets to set for the BPM
        """
        self.__bpm_device.set_offset(offset_values)

