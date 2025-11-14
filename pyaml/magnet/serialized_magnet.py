import numpy as np
from numpy import typing as npt
from pydantic import BaseModel,ConfigDict

from .model import MagnetModel
from ..common.element import Element, ElementConfigModel
from ..control.deviceaccess import DeviceAccess

# Define the main class name for this module
PYAMLCLASS = "SerializedMagnetsModel"


class ConfigModel(ElementConfigModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

    function: str
    """List of magnets"""

    elements: list[str]
    """List of magnets"""

    model: MagnetModel | None = None
    """Object in charge of converting magnet strengths to currents"""


class SerializedMagnetsModel(Element):
    """
    Class managing serialized magnets: a set of magnet with the same set point.
    The set point is usually managed by only one power supply but it can be covered by several ones.
    If several power supplies


    Parameters
    ----------
    cfg : ConfigModel
        Configuration object TODO: to describe

    Raises
    ------
    pyaml.PyAMLException
        In case of wrong initialization
    """

    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg.name)
        self._cfg = cfg
        self.model = cfg.model

    def compute_hardware_values(self, strengths: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        pass

    def compute_strengths(self, hardware_values: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        pass

    def get_strength_units(self) -> list[str]:
        return [self._cfg.unit]*len(self._cfg.elements)

    def get_hardware_units(self) -> list[str]:
        return [device.unit() for device in self.get_devices()]

    def read_hardware_values(self) -> npt.NDArray[np.float64]:
        return np.array([p.get() for p in self.get_devices()])

    def readback_hardware_values(self) -> npt.NDArray[np.float64]:
        return np.array([p.readback() for p in self.get_devices()])

    def send_hardware_values(self, hardware_values: npt.NDArray[np.float64]):
        for idx, p in enumerate(self.get_devices()):
            p.set(hardware_values[idx])

    def get_devices(self) -> list[DeviceAccess]:
        if isinstance(self.model.powerconverter, list):
            return self.model.powerconverter
        else:
            return [self._cfg.powerconverter]

    def set_magnet_rigidity(self, brho: np.double):
        pass
