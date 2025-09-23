import numpy as np
from numpy import typing as npt
from pydantic import BaseModel,ConfigDict

from .model import MagnetModel
from ..control.deviceaccess import DeviceAccess

# Define the main class name for this module
PYAMLCLASS = "SerializedMagnetsModel"


class ConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

    name: str
    """The series name"""

    elements: list[str]
    """List of magnets in the lattice"""

    powerconverter: DeviceAccess | list[DeviceAccess]
    """
    The hardware can be a single power supply or a list of power supplies.
    If a list is provided, the same value will be affected to all of them.
    """

    unit: str
    """Strength unit (i.e. ['rad','m-1','m-2']). All magnets in series have the same unit"""


class SerializedMagnetsModel(MagnetModel):
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
        super().__init__(cfg.name, cfg.linked_elements)
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
        return np.array([p.get() for p in self._cfg.powerconverter])

    def readback_hardware_values(self) -> npt.NDArray[np.float64]:
        return np.array([p.readback() for p in self._cfg.powerconverter])

    def send_hardware_values(self, hardware_values: npt.NDArray[np.float64]):
        for idx, p in enumerate(self._cfg.powerconverter):
            p.set(currents[idx])

    def get_devices(self) -> list[DeviceAccess]:
        if isinstance(self._cfg.powerconverter, list):
            return self._cfg.powerconverter
        else:
            return [self._cfg.powerconverter]

    def set_magnet_rigidity(self, brho: np.double):
        pass
