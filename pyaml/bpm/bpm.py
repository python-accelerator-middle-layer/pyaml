"""Beam-position monitor elements and their runtime interfaces."""

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
        """Initialize a beam-position monitor configuration.

        Parameters
        ----------
        name : str
            BPM element name.
        lattice_names : str | None
            Lattice selector associated with the BPM.
        description : str | None
            Human-readable BPM description.
        x_pos : str | None
            Device key for horizontal position readback.
        y_pos : str | None
            Device key for vertical position readback.
        x_offset : str | None
            Device key for horizontal offset control.
        y_offset : str | None
            Device key for vertical offset control.
        tilt : str | None
            Device key for BPM tilt control.
        """
        super().__init__(name, lattice_names, description)
        self._x_pos = x_pos
        self._y_pos = y_pos
        self._x_offset = x_offset
        self._y_offset = y_offset
        self._tilt_name = tilt
        self._positions = None
        self._offset = None
        self._tilt = None

    @property
    def positions(self) -> ReadFloatArray:
        """
        Get the BPM position readings.

        Returns
        -------
            ReadFloatArray
            Read-only array containing horizontal and vertical positions.

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
            ReadWriteFloatArray
            Read/write array containing horizontal and vertical offsets.

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
            ReadWriteFloatScalar
            Read/write BPM tilt angle used for rotation correction.

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
            Simulator or control-system peer.
        positions : RBpmArray
            Read-only horizontal and vertical position interface.
        offset : RWBpmOffsetArray
            Read/write horizontal and vertical offset interface.
        tilt : RWBpmTiltScalar
            Read/write tilt interface.

        Returns
        -------
        Self
            Shallow copy of this BPM bound to ``peer`` and its interfaces.
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
        Return configured device keys used for position readback.

        Returns
        -------
            list of str or None
            Horizontal and vertical position device keys.
        """
        return [self._x_pos, self._y_pos]

    def get_tilt_device(self) -> str | None:
        """
        Return the configured device key used for tilt access.

        Returns
        -------
            str or None
            Tilt device key.
        """
        return self._tilt_name

    def get_offset_devices(self) -> list[str | None]:
        """
        Return configured device keys used for offset control.

        Returns
        -------
            list of str or None
            Horizontal and vertical offset device keys.
        """
        return [self._x_offset, self._y_offset]

    def __repr__(self):
        """
        Implement the ``__repr__`` string.
        """
        return __pyaml_repr__(self, exclude=["positions", "offset", "tilt"])
