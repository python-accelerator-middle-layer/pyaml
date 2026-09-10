import copy
from typing import Self

from ..common.abstract import ReadFloatArray, ReadWriteFloatArray, ReadWriteFloatScalar
from ..common.element import Element, __pyaml_repr__
from ..common.exception import PyAMLException
from ..validation import DynamicValidation, register_schema

PYAMLCLASS = "BPM"


@register_schema
class BPM(Element, DynamicValidation):
    """
    Beam position monitor (BPM) element.

    Represents a BPM in the accelerator lattice and provides access to its
    associated readback signals, including horizontal and vertical beam
    positions, calibration offsets, and mechanical tilt.

    Parameters
    ----------
    name : str
        Name of the BPM.
    lattice_names : str | None, optional
        Lattice-specific name or names identifying the BPM.
    description : str | None, optional
        Description of the BPM.
    x_pos : str | None, optional
        Device catalog key for the horizontal beam position.
    y_pos : str | None, optional
        Device catalog key for the vertical beam position.
    x_offset : str | None, optional
        Device catalog key for the horizontal BPM offset.
    y_offset : str | None, optional
        Device catalog key for the vertical BPM offset.
    tilt : str | None, optional
        Device catalog key for the BPM tilt.
    """

    __pyaml_repr_exclude__ = ("x_pos", "y_pos", "x_offset", "y_offset", "tilt_name")

    def __init__(
        self,
        name: str,
        lattice_names: str | None = None,
        description: str | None = None,
        x_pos: str | None = None,
        y_pos: str | None = None,
        x_offset: str | None = None,
        y_offset: str | None = None,
        tilt: str | None = None,
    ):
        super().__init__(name, lattice_names, description)
        self.x_pos = x_pos
        self.y_pos = y_pos
        self.x_offset = x_offset
        self.y_offset = y_offset
        self.tilt_name = tilt
        self._positions = None
        self._offset = None
        self._tilt = None

    @property
    def positions(self) -> ReadFloatArray:
        """
        Get the BPM position readings.

        Returns
        -------
        RBpmArray
            BPM position array containing horizontal and vertical positions

        Raises
        ------
        PyAMLException
            If positions have not been attached
        """
        if self._positions is None:
            raise PyAMLException(f"{str(self)} has no attached positions")
        return self._positions

    @property
    def offset(self) -> ReadWriteFloatArray:
        """
        Get the BPM offset values.

        Returns
        -------
        RWBpmOffsetArray
            BPM offset array for position correction

        Raises
        ------
        PyAMLException
            If offset has not been attached
        """
        if self._offset is None:
            raise PyAMLException(f"{str(self)} has no attached offset")
        return self._offset

    @property
    def tilt(self) -> ReadWriteFloatScalar:
        """
        Get the BPM tilt angle.

        Returns
        -------
        RWBpmTiltScalar
            BPM tilt angle for rotation correction

        Raises
        ------
        PyAMLException
            If tilt has not been attached
        """
        if self._tilt is None:
            raise PyAMLException(f"{str(self)} has no attached tilt")
        return self._tilt

    def attach(
        self,
        peer,
        positions: ReadFloatArray,
        offset: ReadWriteFloatArray,
        tilt: ReadWriteFloatScalar,
    ) -> Self:
        """
        Attach BPM attributes to a peer.

        Parameters
        ----------
        peer : object
            The peer object (simulator or control system)
        positions : RBpmArray
            BPM position readings
        offset : RWBpmOffsetArray
            BPM offset values for correction
        tilt : RWBpmTiltScalar
            BPM tilt angle for rotation correction

        Returns
        -------
        Self
            A new attached instance of BPM
        """
        # Attach positions, offset and tilt attributes and returns a new
        # reference
        obj = copy.copy(self)
        obj._positions = positions
        obj._offset = offset
        obj._tilt = tilt
        obj._peer = peer
        return obj

    def get_pos_devices(self) -> list[str | None]:
        """
        Get device handles used for position reading

        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAcess
        """
        return [self.x_pos, self.y_pos]

    def get_tilt_device(self) -> str | None:
        """
        Get device handle used for tilt access

        Returns
        -------
        DeviceAccess
            DeviceAcess
        """
        return self.tilt_name

    def get_offset_devices(self) -> list[str | None]:
        """
        Get device handles used for offset access

        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAcess
        """
        return [self.x_offset, self.y_offset]

    def __repr__(self):
        return __pyaml_repr__(self, exclude=["positions", "offset", "tilt"])
