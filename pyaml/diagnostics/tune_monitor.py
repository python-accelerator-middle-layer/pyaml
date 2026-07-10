import copy
from typing import Self

from numpy.typing import NDArray

from ..common.abstract import ReadFloatArray
from ..common.element import Element
from ..validation import DynamicValidation, register_schema
from .atune_monitor import ABetatronTuneMonitor

PYAMLCLASS = "BetatronTuneMonitor"


@register_schema
class BetatronTuneMonitor(Element, DynamicValidation, ABetatronTuneMonitor):
    """
    Betatron tune monitor.

    Represents a betatron tune monitor in the accelerator lattice and
    provides access to the measured horizontal and vertical betatron
    tunes. Optionally, the monitor can be associated with an RF plant
    used to convert tune measurements to frequency values.

    Parameters
    ----------
    name : str
        Name of the betatron tune monitor.
    description : str | None, optional
        Description of the monitor.
    tune_h : str | None, optional
        Device catalog key for the horizontal betatron tune measurement.
    tune_v : str | None, optional
        Device catalog key for the vertical betatron tune measurement.
    rf_plant_name : str | None, optional
        Name of the associated RF plant element used by the monitor.
    """

    def __init__(
        self,
        name: str,
        description: str | None = None,
        tune_h: str | None = None,
        tune_v: str | None = None,
        rf_plant_name: str | None = None,
    ):
        super().__init__(name, None, description)
        self._tune_h = tune_h
        self._tune_v = tune_v
        self._rf_plant_name = rf_plant_name
        self.__tune = None
        self._h = None

    def set_harmonic(self, h: int):
        self._h = float(h)

    @property
    def tune_h(self) -> str | None:
        return self._tune_h

    @property
    def tune_v(self) -> str | None:
        return self._tune_v

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

            def get(self) -> NDArray:
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
        obj = copy.copy(self)
        obj.__tune = betatron_tune
        obj._peer = peer
        return obj
