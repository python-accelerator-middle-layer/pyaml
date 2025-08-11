import numpy as np
from numpy import typing as npt
from pydantic import BaseModel,ConfigDict

from .model import MagnetModel
from ..control.deviceaccess import DeviceAccess

# Define the main class name for this module
PYAMLCLASS = "SerializedMagnetsModel"


class ConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")


class SerializedMagnetsModel(MagnetModel):
    """SerializedMagnetsModel class"""

    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg.name, cfg.linked_elements)
        self._cfg = cfg
        self.model = cfg.model

    def compute_hardware_values(self, strengths: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        pass

    def compute_strengths(self, hardware_values: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        pass

    def get_strength_units(self) -> list[str]:
        pass

    def get_hardware_units(self) -> list[str]:
        pass

    def read_hardware_values(self) -> npt.NDArray[np.float64]:
        pass

    def readback_hardware_values(self) -> npt.NDArray[np.float64]:
        pass

    def send_hardware_values(self, hardware_values: npt.NDArray[np.float64]):
        pass

    def get_devices(self) -> list[DeviceAccess]:
        pass

    def set_magnet_rigidity(self, brho: np.double):
        pass
