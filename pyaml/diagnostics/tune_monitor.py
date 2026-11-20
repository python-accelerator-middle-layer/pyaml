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
from ..common.exception import PyAMLConfigException, PyAMLException
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
    tunes.

    The tune devices may report the fractional tune (unit ``"1"`` or no
    unit) or the betatron frequency, in any frequency unit (``Hz``,
    ``kHz``...). The fractional tune ``q`` is then computed from the
    frequency ``f`` and the revolution frequency of the RF plant.

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
    tune_above_half : list[bool] | None, optional
        ``[horizontal, vertical]`` flags, only used for a tune device
        reporting a frequency: ``True`` when the fractional tune of the plane
        is above the half-integer. Defaults to ``[False, False]``.

    Attributes
    ----------
    tune_h
        Return the horizontal tune device catalog key.
    tune_v
        Return the vertical tune device catalog key.
    rf_plant_name
        Return the name of the RF plant used for tune-frequency conversion.
    tune_above_half
        Return the ``[horizontal, vertical]`` above-half-integer flags.
    tune
        Get the betatron tune values.
    frequency
        Return the betatron tune values converted to frequency.

    Methods
    -------
    attach(peer, betatron_tune)
        Attach the tune monitor to a peer with betatron tune data.

    Configuration
    -------------
    .. code-block:: yaml

        - type: pyaml.diagnostics.tune_monitor
          name: BETATRON_TUNE
          tune_h: DEVICE/HORIZONTAL_TUNE
          tune_v: DEVICE/VERTICAL_TUNE
          rf_plant_name: RF
          tune_above_half: [false, false]
    """

    def __init__(
        self,
        name: str,
        description: str | None = None,
        tune_h: str | None = None,
        tune_v: str | None = None,
        rf_plant_name: str | None = None,
        tune_above_half: list[bool] | None = None,
    ):
        """
        Initialize a betatron tune monitor.
        """
        super().__init__(name, None, description)
        self._tune_h = tune_h
        self._tune_v = tune_v
        self._rf_plant_name = rf_plant_name
        if tune_above_half is None:
            tune_above_half = [False, False]
        if len(tune_above_half) != 2:
            raise PyAMLConfigException(
                f"{name}: tune_above_half expects 2 values [horizontal, vertical], got {tune_above_half}"
            )
        self._tune_above_half = [bool(a) for a in tune_above_half]
        self.__tune = None

    def _rf_plant(self):
        """Return the RF plant of the mode the monitor is attached to."""
        if self._rf_plant_name is None:
            raise PyAMLException(f"{self.get_name()}: rf_plant_name is required to compute the revolution frequency")
        self.check_peer()
        return self.peer.rf.get(self._rf_plant_name)

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
    def rf_plant_name(self) -> str | None:
        """Return the name of the RF plant used for tune-frequency conversion."""
        return self._rf_plant_name

    @property
    def tune_above_half(self) -> list[bool]:
        """Return the ``[horizontal, vertical]`` above-half-integer flags."""
        return list(self._tune_above_half)

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
                Return the pyAML unit for this quantity, i.e. returned by get().
            """

            def __init__(self, parent: BetatronTuneMonitor):
                """
                Initialize the tune-frequency view.
                """
                self.parent = parent

            def get(self) -> NDArray:
                """Return tune frequencies in hertz."""
                return self.parent.tune.get() * self.parent._rf_plant().revolution_frequency()

            def unit(self) -> str:
                """Return the pyAML unit for this quantity, i.e. returned by get()."""
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
