from ..common.abstract import ReadFloatArray
from ..common.element import Element, ElementSchema
from ..control.deviceaccess import DeviceAccess, DeviceAccessSchema
from .atune_monitor import ABetatronTuneMonitor

try:
    from typing import Self  # Python 3.11+
except ImportError:
    from typing_extensions import Self  # Python 3.10 and earlier
import numpy as np
from pydantic import ConfigDict

PYAMLCLASS = "BetatronTuneMonitor"


class ConfigModel(ElementSchema):
    """
    Configuration model for BetatronTuneMonitor

    Parameters
    ----------
    tune_h : DeviceAccess, optional
        Horizontal betatron tune device
    tune_v : DeviceAccess, optional
        Vertical betatron tune device
    """

    model_config = ConfigDict(extra="forbid")

    tune_h: DeviceAccessSchema | None = None
    tune_v: DeviceAccessSchema | None = None
    rf_plant_name: str | None = None


class BetatronTuneMonitor(Element, ABetatronTuneMonitor):
    """
    Class providing access to a betatron tune monitor
    of a physical or simulated lattice.
    The monitor provides horizontal and vertical betatron tune measurements.
    """

    def __init__(
        self,
        name: str,
        tune_h: DeviceAccess | None = None,
        tune_v: DeviceAccess | None = None,
        rf_plant_name: str | None = None,
    ):
        """
        Construct a BetatronTuneMonitor
        """

        super().__init__(name)

        self._tune_h = tune_h
        self._tune_v = tune_v
        self._rf_plant_name = rf_plant_name

        self.__tune = None
        self._h = None

    def set_harmonic(self, h: int):
        self._h = float(h)

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

    @property
    def frequency(self) -> ReadFloatArray:
        """
        Get the betatron tune values in frequency

        Returns
        -------
        ReadFloatArray
            Array of tune values in frequency [horizontal, vertical]
        """

        class TuneFreq(ReadFloatArray):
            def __init__(self, parent: BetatronTuneMonitor):
                self.parent = parent

            def get(self) -> np.array:
                h = self.parent._h
                rf_name = self.parent._rf_plant_name
                if h is not None and rf_name is not None:
                    tune = self.parent.tune.get()
                    rf = self.parent.peer.get_rf_plant(rf_name)
                    freq = rf.frequency.get()
                    return tune * freq / h

            def unit(self) -> str:
                return "Hz"

        self.check_peer()
        return TuneFreq(self)

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
        obj = self.__class__(self._name, self._tune_h, self._tune_v, self._rf_plant_name)
        obj.__tune = betatron_tune
        obj._peer = peer
        return obj
