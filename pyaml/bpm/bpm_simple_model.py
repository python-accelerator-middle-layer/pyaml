import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict

from pyaml.bpm.bpm_model import BPMModel

from ..common.element import __pyaml_repr__
from ..configuration.catalog import Catalog
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

    x_pos_index: int | None = None
    y_pos_index: int | None = None
    x_pos: str = "x_pos"
    y_pos: str = "y_pos"
    positions: str = "positions"


class BPMSimpleModel(BPMModel):
    """
    Concrete implementation of BPMModel that simulates a BPM with tilt and
    offset values.
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg

    def get_pos_devices(self, name: str, catalog: Catalog) -> list[DeviceAccess | None]:
        """
        Get device handles used for position reading

        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAccess
        """
        if self.is_pos_indexed():
            ref = name + "/" + self._cfg.positions
            dev = catalog.get_one(ref)
            pos_devices = [dev, dev]
        else:
            x_ref = name + "/" + self._cfg.x_pos
            y_ref = name + "/" + self._cfg.y_pos
            pos_devices = [catalog.get_one(x_ref), catalog.get_one(y_ref)]
        return pos_devices

    def get_tilt_device(self, name: str, catalog: Catalog) -> DeviceAccess | None:
        """
        Get device handle used for tilt access

        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAccess
        """
        return None

    def get_offset_devices(
        self, name: str, catalog: Catalog
    ) -> list[DeviceAccess | None]:
        """
        Get device handles used for offset access

        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAccess
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
