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


class BPMTiltOffsetModel(BPMSimpleModel):
    """
    Concrete implementation of BPMModel that simulates a BPM with tilt and
    offset values.
    """

    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg)

    def get_tilt_device(self, name: str, catalog: Catalog) -> DeviceAccess | None:
        """
        Get device handle used for tilt access

        Returns
        -------
        DeviceAccess
            The DeviceAccess for tilt
        """
        if catalog.has_reference(name + "/tilt"):
            return catalog.get_one(name + "/tilt")
        return None

    def get_offset_devices(
        self, name: str, catalog: Catalog
    ) -> list[DeviceAccess | None]:
        """
        Get device handles used for offset access

        Returns
        -------
        list[DeviceAccess]
            Array of 2 DeviceAccess: [x_offset, y_offset]
        """
        if catalog.has_reference(name + "/offsets"):
            return catalog.get_many(name + "/offsets")[:2]
        return [None, None]

    def __repr__(self):
        return __pyaml_repr__(self)
