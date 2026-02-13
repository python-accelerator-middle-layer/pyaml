import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict

from pyaml.bpm.bpm_model import BPMModel
from pyaml.bpm.bpm_simple_model import BPMSimpleModel

from ..common.element import __pyaml_repr__
from ..configuration.catalog import Catalog
from ..control.deviceaccess import DeviceAccess

# Define the main class name for this module
PYAMLCLASS = "BPMTiltOffsetModel"

# TODO: Implepement indexed offset and tilt


class ConfigModel(BaseModel):
    """
    Configuration model for BPM with tilt and offset

    Parameters
    ----------
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
    tilt: str = None
    x_offset: str = None
    y_offset: str = None


class BPMTiltOffsetModel(BPMSimpleModel):
    """
    Concrete implementation of BPMModel that simulates a BPM with tilt and
    offset values.
    """

    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg)

    def get_tilt_device(self) -> str | None:
        """
        Get device handle used for tilt access

        Returns
        -------
        str | None
            tilt naming
        """
        return self._cfg.tilt

    def get_x_offset_device(self) -> str | None:
        """
        Get device handles used for offset access

        Returns
        -------
        str | None
            h offset naming
        """
        return self._cfg.x_offset

    def get_y_offset_device(self) -> str | None:
        """
        Get device handles used for offset access

        Returns
        -------
        str | None
            v offset naming
        """
        return self._cfg.y_offset

    def __repr__(self):
        return __pyaml_repr__(self)
