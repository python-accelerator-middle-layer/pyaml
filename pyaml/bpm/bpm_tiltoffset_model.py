import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict

from pyaml.bpm.bpm_model import BPMModel
from pyaml.bpm.bpm_simple_model import BPMSimpleModel, BPMSimpleModelSchema

from ..common.element import __pyaml_repr__
from ..configuration.schema_registry import register_schema
from ..control.deviceaccess import DeviceAccess

# TODO: Implepement indexed offset and tilt


class BPMTiltOffsetModelSchema(BPMSimpleModelSchema):
    """
    Configuration model for BPM with tilt and offset

    Parameters
    ----------
    x_pos : DeviceAccess, optional
        Horizontal position device
    y_pos : DeviceAccess, optional
        Vertical position device
    x_offset : DeviceAccess, optional
        Horizontal BPM offset device
    y_offset : DeviceAccess, optional
        Vertical BPM offset device
    tilt : DeviceAccess, optional
        BPM tilt device
    """

    model_config = ConfigDict(extra="forbid")

    x_offset: DeviceAccess | None = None
    y_offset: DeviceAccess | None = None
    tilt: DeviceAccess | None = None


@register_schema(BPMTiltOffsetModelSchema)
class BPMTiltOffsetModel(BPMSimpleModel):
    """
    Concrete implementation of BPMModel that simulates a BPM with tilt and
    offset values.
    """

    def __init__(
        self,
        x_pos: DeviceAccess | None,
        y_pos: DeviceAccess | None,
        x_pos_index: int | None = None,
        y_pos_index: int | None = None,
        x_offset: DeviceAccess | None = None,
        y_offset: DeviceAccess | None = None,
        tilt: DeviceAccess | None = None,
    ):
        super().__init__(x_pos=x_pos, y_pos=y_pos, x_pos_index=x_pos_index, y_pos_index=y_pos_index)

        self.__x_offset = x_offset
        self.__y_offset = y_offset
        self.__tilt = tilt

    def get_pos_devices(self) -> list[DeviceAccess | None]:
        """
        Get device handles used for position reading

        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAcess
        """
        return [self.__x_pos, self.__y_pos]

    def get_tilt_device(self) -> DeviceAccess | None:
        """
        Get device handle used for tilt access

        Returns
        -------
        DeviceAccess
            DeviceAcess
        """
        return self.__tilt

    def get_offset_devices(self) -> list[DeviceAccess | None]:
        """
        Get device handles used for offset access

        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAcess
        """
        return [self.__x_offset, self.__y_offset]


#    def __repr__(self):
#        return __pyaml_repr__(self)
