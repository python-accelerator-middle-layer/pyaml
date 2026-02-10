from ..bpm.bpm_model import BPMModel
from ..common.element import Element, ElementConfigModel
from ..common.exception import PyAMLException
from ..lattice.abstract_impl import RBpmArray, RWBpmOffsetArray, RWBpmTiltScalar

try:
    from typing import Self  # Python 3.11+
except ImportError:
    from typing_extensions import Self  # Python 3.10 and earlier

PYAMLCLASS = "BPM"


class ConfigModel(ElementConfigModel):
    """
    Configuration model for BPM element.

    Attributes
    ----------
    model : BPMModel or None, optional
        Object in charge of BPM modeling
    """

    model: BPMModel | None = None


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
        self.__positions = None
        self.__offset = None
        self.__tilt = None

    @property
    def model(self) -> BPMModel:
        """
        Get the BPM model.

        Returns
        -------
        BPMModel
            The BPM model instance
        """
        return self.__model

    @property
    def positions(self) -> RBpmArray:
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
        if self.__positions is None:
            raise PyAMLException(f"{str(self)} has no attached positions")
        return self.__positions

    @property
    def offset(self) -> RWBpmOffsetArray:
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
        if self.__offset is None:
            raise PyAMLException(f"{str(self)} has no attached offset")
        return self.__offset

    @property
    def tilt(self) -> RWBpmTiltScalar:
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
        if self.__tilt is None:
            raise PyAMLException(f"{str(self)} has no attached tilt")
        return self.__tilt

    def attach(
        self,
        peer,
        positions: RBpmArray,
        offset: RWBpmOffsetArray,
        tilt: RWBpmTiltScalar,
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
        obj.__positions = positions
        obj.__offset = offset
        obj.__tilt = tilt
        obj._peer = peer
        return obj
