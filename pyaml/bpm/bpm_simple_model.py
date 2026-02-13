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
    x_pos: str = None
    y_pos: str = None
    positions: str = None


class BPMSimpleModel(BPMModel):
    """
    Concrete implementation of BPMModel that simulates a BPM with tilt and
    offset values.
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg

    def get_positions_device(self) -> str | None:
        """
        Get device handles used for position reading

        Returns
        -------
        str | None
            h and v positions naming
        """
        return self._cfg.positions

    def get_x_pos_device(self) -> str | None:
        """
        Get device handles used for position reading

        Returns
        -------
        str | None
            h position naming
        """
        return self._cfg.x_pos

    def get_y_pos_device(self) -> str | None:
        """
        Get device handles used for position reading

        Returns
        -------
        str | None
            v position naming
        """
        return self._cfg.y_pos

    def get_tilt_device(self) -> str | None:
        """
        Get device handle used for tilt access

        Returns
        -------
        str | None
            tilt naming
        """
        return None

    def get_x_offset_device(self) -> str | None:
        """
        Get device handles used for offset access

        Returns
        -------
        str | None
            h offset naming
        """
        return None

    def get_y_offset_device(self) -> str | None:
        """
        Get device handles used for offset access

        Returns
        -------
        str | None
            v offset naming
        """
        return None

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
