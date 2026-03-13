import numpy as np
from pydantic import BaseModel, ConfigDict

from ..common.element import __pyaml_repr__
from ..configuration.curve import Curve
from ..control.deviceaccess import DeviceAccess
from .magnet import Magnet
from .model import MagnetModel

# Define the main class name for this module
PYAMLCLASS = "WindingModel"


class ConfigModel(BaseModel):
    """
    Winding model.

    Parameters
    ----------
    powerconverter : DeviceAccess or None, optional
        Power converter device to apply currrent
    attached_magnet_name : str
        Name of magnet to which this winding is attached.
        The model uses this magnet's calibration curves.
    winding_ratio : float, optional
        Calibration constant such that K = I2K( I1 + R * I2 ).
        Ideally corresponds to the ratio of windings around the yoke
        between this magnet and the attached magnet (typically a magnet
        in series with other magnets) Default: 1.0
    unit : str
        Unit of the strength (i.e. 1/m or m-1)

    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    powerconverter: DeviceAccess | None
    attached_magnet_name: str
    winding_ratio: float = 1.0
    unit: str


class WindingModel(MagnetModel):
    """
    Class that handle magnet current/strength conversion of an extra winding attached
    to another magnet, using that other magnet's calibration curve.

    K2 = I2K( I1 + R * I2) - K1
    K1 = I2K( I1 )
    I2 = ( K2I( K2 - K1 ) - I1 ) / R
    I1 = K2I( K1 )
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        self._winding_ratio = cfg.winding_ratio
        self._attached_magnet_name = cfg.attached_magnet_name
        self._attached_magnet: "Magnet" = None

        self.__strength_unit = cfg.unit
        self.__hardware_unit = cfg.powerconverter.unit()
        self.__brho = np.nan
        self.__ps = cfg.powerconverter

    def compute_hardware_values(self, strengths: np.array) -> np.array:
        # TODO: assumes all are the same
        strength0 = self._attached_magnet.strengths.get()[0]
        hardware0 = self._attached_magnet.hardwares.get()[0]

        model = self._attached_magnet.model
        total_current = model.compute_hardware_values(strength0 - strengths)
        hardware = (total_current - hardware0) / self._winding_ratio
        return np.array([hardware])

    def compute_strengths(self, currents: np.array) -> np.array:
        # TODO: assumes all are the same
        strength0 = self._attached_magnet.strengths.get()[0]
        hardware0 = self._attached_magnet.hardwares.get()[0]
        model = self._attached_magnet.model

        total_strength = model.compute_strengths(
            hardware0 + self._winding_ratio * currents
        )
        strength = total_strength - strength0
        return np.array([strength])

    def get_strength_units(self) -> list[str]:
        return [self.__strength_unit] if self.__strength_unit is not None else [""]

    def get_hardware_units(self) -> list[str]:
        return [self.__hardware_unit] if self.__hardware_unit is not None else [""]

    def get_devices(self) -> list[DeviceAccess]:
        return [self.__ps]

    def set_magnet_rigidity(self, brho: np.double):
        self.__brho = brho

    def post_init(self):
        element_holder = self._peer
        self._attached_magnet = element_holder.get_magnet(self._attached_magnet_name)

    def __repr__(self):
        return __pyaml_repr__(self)
