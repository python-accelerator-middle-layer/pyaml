import numpy as np
from numpy.typing import NDArray

from pyaml.bpm.bpm_model import BPMModel

from ..common.element import __pyaml_repr__
from ..control.deviceaccess import DeviceAccess, DeviceAccessSchema
from ..validation import register_schema
from .bpm_model import BPMModelSchema


class BPMSimpleModelSchema(BPMModelSchema):
    """
    Configuration model for BPM simple model

    Parameters
    ----------
    x_pos : DeviceAccessSchema, optional
        Horizontal position device
    y_pos : DeviceAccessSchema, optional
        Vertical position device
    x_pos_index : int, optional
        Index in the array when specified, otherwise scalar
        value is expected
    y_pos_index : int, optional
        Index in the array when specified, otherwise scalar
        value is expected
    """

    x_pos: DeviceAccessSchema | None = None
    y_pos: DeviceAccessSchema | None = None
    x_pos_index: int | None = None
    y_pos_index: int | None = None


@register_schema(BPMSimpleModelSchema)
class BPMSimpleModel(BPMModel):
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
    ):
        self.__x_pos = x_pos
        self.__y_pos = y_pos
        self.__x_pos_index = x_pos_index
        self.__y_pos_index = y_pos_index

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
        list[DeviceAccess]
            Array of DeviceAcess
        """
        return None

    def get_offset_devices(self) -> list[DeviceAccess | None]:
        """
        Get device handles used for offset access

        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAcess
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
        return self.__x_pos_index

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
        return self.__.y_pos_index


#    def __repr__(self):
#        return __pyaml_repr__(self)
