from ..common.abstract import ReadFloatArray
from ..common.element import Element, ElementConfigModel
from ..control.deviceaccess import DeviceAccess

try:
    from typing import Self  # Python 3.11+
except ImportError:
    from typing_extensions import Self  # Python 3.10 and earlier
from pydantic import ConfigDict

PYAMLCLASS = "BetatronTuneMonitor"


class ConfigModel(ElementConfigModel):
    """
    Configuration model for BetatronTuneMonitor

    Parameters
    ----------
    tune_h : DeviceAccess, optional
        Horizontal betatron tune device
    tune_v : DeviceAccess, optional
        Vertical betatron tune device
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    tune_h: DeviceAccess | None
    tune_v: DeviceAccess | None


class BetatronTuneMonitor(Element):
    """
    Class providing access to a betatron tune monitor
    of a physical or simulated lattice.
    The monitor provides horizontal and vertical betatron tune measurements.
    """

    def __init__(self, cfg: ConfigModel):
        """
        Construct a BetatronTuneMonitor

        Parameters
        ----------
        cfg : ConfigModel
            Configuration for the BetatronTuneMonitor, including
            device access for horizontal and vertical tunes.
        """

        super().__init__(cfg.name)
        self._cfg = cfg
        self.__tune = None

    @property
    def tune(self) -> ReadFloatArray:
        """
        Get the betatron tune values.

        Returns
        -------
        ReadFloatArray
            Array of tune values [horizontal, vertical]
        """
        self.check_peer()
        return self.__tune

    def attach(self, peer, betatron_tune: ReadFloatArray) -> Self:
        """
        Attach the tune monitor to a peer with betatron tune data.

        Parameters
        ----------
        peer : object
            The peer object (simulator or control system)
        betatron_tune : ReadFloatArray
            The betatron tune array to monitor

        Returns
        -------
        Self
            A new attached instance of TuneMonitor
        """
        obj = self.__class__(self._cfg)
        obj.__tune = betatron_tune
        obj._peer = peer
        return obj
