"""
Betatron tune monitor element and runtime data bindings.

The monitor identifies tune measurements, attaches them to a runtime peer,
and optionally converts tune fractions to frequencies using an RF plant.
"""

import copy
from typing import TYPE_CHECKING, Self

from numpy.typing import NDArray

from ..common.abstract import ReadFloatArray
from ..common.element import Element, __pyaml_repr__
from ..validation import DynamicValidation, register_schema
from .atune_monitor import ABetatronTuneMonitor

if TYPE_CHECKING:
    from ..common.holders.element_holder import ElementHolder

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

    Attributes
    ----------
    tune_h
        Return the horizontal tune device catalog key.
    tune_v
        Return the vertical tune device catalog key.
    tune
        Get the betatron tune values.
    frequency
        Return the betatron tune values converted to frequency.

    Methods
    -------
    set_harmonic(h)
        Set the harmonic number used for tune-frequency conversion.
    attach(peer, betatron_tune)
        Attach the tune monitor to a peer with betatron tune data.
    """

    def __init__(
        self,
        name: str,
        description: str | None = None,
        tune_h: str | None = None,
        tune_v: str | None = None,
        rf_plant_name: str | None = None,
    ):
        """
        Initialize a betatron tune monitor.
        """
        super().__init__(name, None, description)
        self._tune_h = tune_h
        self._tune_v = tune_v
        self._rf_plant_name = rf_plant_name
        self.__tune = None
        self._h = None

    def set_harmonic(self, h: int):
        """
        Set the harmonic number used for tune-frequency conversion.

        Parameters
        ----------
        h : int
            Harmonic number relating the RF frequency to the measured
            betatron tune frequency.
        """
        self._h = float(h)

    def _fill_device(self, holder: "ElementHolder") -> None:
        holder._fill_betatron_tune_monitor(self)

    @property
    def tune_h(self) -> str | None:
        """Return the horizontal tune device catalog key."""
        return self._tune_h

    @property
    def tune_v(self) -> str | None:
        """Return the vertical tune device catalog key."""
        return self._tune_v

    @property
    def tune(self) -> ReadFloatArray:
        """
        Get the betatron tune values.

        Returns
        -------
        ReadFloatArray
            Readable array containing the horizontal and vertical tunes.
        """
        self.check_peer()
        return self.__tune

    @property
    def frequency(self) -> ReadFloatArray:
        """
        Return the betatron tune values converted to frequency.

        Returns
        -------
        ReadFloatArray
            Readable array containing horizontal and vertical frequencies.
        """

        class TuneFreq(ReadFloatArray):
            """
            Read-only view that converts tune values to frequencies.

            Parameters
            ----------
            parent : BetatronTuneMonitor
                Monitor providing the source tune and RF data.

            Methods
            -------
            get()
                Return tune frequencies in hertz.
            unit()
                Return the frequency unit label.
            """

            def __init__(self, parent: BetatronTuneMonitor):
                """
                Initialize the tune-frequency view.
                """
                self.parent = parent

            def get(self) -> NDArray:
                """Return tune frequencies in hertz."""
                h = self.parent._h
                rf_name = self.parent._rf_plant_name
                if h is not None and rf_name is not None:
                    tune = self.parent.tune.get()
                    rf = self.parent.peer.rf.get(rf_name)
                    freq = rf.frequency.get()
                    return tune * freq / h

            def unit(self) -> str:
                """Return the frequency unit label."""
                return "Hz"

        self.check_peer()
        return TuneFreq(self)

    def attach(self, peer, betatron_tune: ReadFloatArray) -> Self:
        """
        Attach the tune monitor to a peer with betatron tune data.

        Parameters
        ----------
        peer : object
            Simulator or control-system peer providing the RF plant.
        betatron_tune : ReadFloatArray
            Readable array containing the measured horizontal and vertical
            tunes.

        Returns
        -------
        Self
            A shallow copy of this monitor bound to ``peer`` and
            ``betatron_tune``.
        """
        obj = copy.copy(self)
        obj.__tune = betatron_tune
        obj._peer = peer
        return obj

    def __repr__(self):
        """
        Implement the ``__repr__`` string.
        """
        return __pyaml_repr__(self, exclude=["tune", "frequency"])
