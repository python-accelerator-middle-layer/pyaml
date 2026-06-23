from ..common.abstract import ReadFloatArray, ReadWriteFloatArray, ReadWriteFloatScalar
from ..common.element import Element, ElementConfigModel
from ..common.exception import PyAMLException

try:
    from typing import Self  # Python 3.11+
except ImportError:
    from typing_extensions import Self  # Python 3.10 and earlier

PYAMLCLASS = "BPM"


class ConfigModel(ElementConfigModel):
    """
    Configuration model for BPM element.

    Parameters
    ----------
    x_pos : str
        Horizontal position device catalog key
    y_pos : str
        Vertical position device catalog key
    x_offset : str
        Horizontal BPM offset device catalog key
    y_offset : str
        Vertical BPM offset device catalog key
    tilt : str
        BPM tilt device catalog key
    """

    x_pos: str | None = None
    y_pos: str | None = None
    x_offset: str | None = None
    y_offset: str | None = None
    tilt: str | None = None


class BPM(Element):
    """
    Class providing access to one BPM of a physical or simulated lattice
    """

    def __init__(self, cfg: ConfigModel):
        """
        Construct a BPM

        Parameters
        ----------
        name : str
            Element name
        model : BPMModel
            BPM model in charge of computing beam position
        """

        super().__init__(cfg.name)

        self.__model = cfg.model if hasattr(cfg, "model") else None
        self._cfg = cfg
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
        obj = self.__class__(self._cfg)
        obj.__model = self.__model
        obj._positions = positions
        obj._offset = offset
        obj._tilt = tilt
        obj._peer = peer
        return obj

    def get_pos_devices(self) -> list[str]:
        """
        Get device handles used for position reading

        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAcess
        """
        return [self._cfg.x_pos, self._cfg.y_pos]

    def get_tilt_device(self) -> str | None:
        """
        Get device handle used for tilt access

        Returns
        -------
        DeviceAccess
            DeviceAcess
        """
        return self._cfg.tilt

    def get_offset_devices(self) -> list[str | None]:
        """
        Get device handles used for offset access

        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAcess
        """
        return [self._cfg.x_offset, self._cfg.y_offset]
