"""
Adapter between PyAML elements and pySC measurement applications.

The :class:`pySCInterface` exposes the orbit, magnet-strength, and RF-frequency
operations expected by pySC while using PyAML element-holder accessors.
"""

import time
from typing import TYPE_CHECKING, Callable, Optional, Tuple

import numpy as np

if TYPE_CHECKING:
    from ..common.holders.element_holder import ElementHolder
from ..common.constants import Action
from ..common.exception import PyAMLException


class pySCInterface:
    """
    Provide pySC-compatible access to a PyAML accelerator mode.

    Parameters
    ----------
    element_holder : 'ElementHolder'
        Accelerator mode, control system or simulator, exposed to pySC.
    bpm_array_name : str
        Name of the BPM array used for orbit readback.
    rf_plant_name : Optional[str]
        Optional RF plant name, required for RF-related pySC operations.
    callback : Callable, optional
        Called as ``callback(action, data)`` with ``Action.BEFORE_BPM_READING``
        before each BPM acquisition.  Return ``True`` to continue;
        a false value raises ``KeyboardInterrupt``.
    orbits_to_average : int, default 1
        Positive number of BPM acquisitions to average per ``get_orbit()`` call.

    Raises
    ------
    ValueError
        If ``orbits_to_average`` is not a positive integer.

    Methods
    -------
    get_orbit()
        Return horizontal and vertical orbit readings from the BPM array.
    get(name)
        Return the current strength of a named magnet.
    set(name, value)
        Set the strength of a named magnet and wait for the configured delay.
    get_rf_main_frequency()
        Return the main RF frequency from the configured RF plant.
    set_rf_main_frequency(value)
        Set the main RF frequency and wait for the configured delay.
    """

    set_wait_time: float = 0
    read_wait_time: float = 0
    orbits_to_average: int = 1

    def __init__(
        self,
        element_holder: "ElementHolder",
        bpm_array_name: str,
        rf_plant_name: Optional[str] = None,
        callback: Optional[Callable] = None,
        orbits_to_average: int = 1,
    ):
        """
        Initialize a pySC adapter from a PyAML element holder.
        """
        if not isinstance(orbits_to_average, (int, np.integer)) or orbits_to_average < 1:
            raise ValueError("orbits_to_average must be a positive integer.")

        self.element_holder = element_holder

        self.bpm_array = element_holder.diagnostic.bpms.get(bpm_array_name)

        self.rf_plant_name = rf_plant_name
        if rf_plant_name is not None:
            self.rf_plant = element_holder.rf.get(self.rf_plant_name)
        else:
            self.rf_plant = None

        self._callback = callback
        self.orbits_to_average = orbits_to_average

    @property
    def peer(self) -> "ElementHolder":
        return self.element_holder

    def attached_to(self) -> str:
        """Return the peer type and name, or ``"None"`` when unattached."""
        return "None" if self.peer is None else f"{self.peer.__class__.__name__}:{self.peer.name()}"

    def get_orbit(self) -> Tuple[np.array, np.array]:
        """Return mean horizontal and vertical orbits over ``orbits_to_average`` reads.

        Invoke ``Action.BEFORE_BPM_READING`` before each acquisition and its
        ``read_wait_time`` delay, including each sample used in the average.
        """
        self.send_callback(Action.BEFORE_BPM_READING, {})
        time.sleep(self.read_wait_time)
        positions = self.bpm_array.positions.get()
        x = positions[:, 0] / self.orbits_to_average
        y = positions[:, 1] / self.orbits_to_average

        for _ in range(1, self.orbits_to_average):
            self.send_callback(Action.BEFORE_BPM_READING, {})
            time.sleep(self.read_wait_time)
            positions = self.bpm_array.positions.get()
            x += positions[:, 0] / self.orbits_to_average
            y += positions[:, 1] / self.orbits_to_average
        return x, y

    def get(self, name: str) -> float:
        """
        Return the current strength of a named magnet.

        Parameters
        ----------
        name : str
            Magnet name in the configured element holder.

        Returns
        -------
        float
            Current magnet strength.
        """
        magnet = self.element_holder.magnet.get(name=name)
        return magnet.strength.get()

    def set(self, name: str, value: float) -> None:
        """
        Set the strength of a named magnet and wait for the configured delay.

        Parameters
        ----------
        name : str
            Magnet name in the configured element holder.
        value : float
            New magnet strength.

        Returns
        -------
        None
            This method does not return a value.
        """
        magnet = self.element_holder.magnet.get(name=name)
        magnet.strength.set(value=value)  # ideally set_and_wait but not implemented
        time.sleep(self.set_wait_time)
        return

    def get_rf_main_frequency(self) -> float:
        """Return the main RF frequency from the configured RF plant."""
        if self.rf_plant is None:
            raise PyAMLException("RF plant name was not provided.")
        return self.rf_plant.frequency.get()

    def set_rf_main_frequency(self, value: float) -> None:
        """
        Set the main RF frequency and wait for the configured delay.

        Parameters
        ----------
        value : float
            New main RF frequency in hertz.

        Returns
        -------
        None
            This method does not return a value.
        """
        if self.rf_plant is None:
            raise PyAMLException("RF plant name was not provided.")
        self.rf_plant.frequency.set(value)
        time.sleep(self.set_wait_time)
        return

    # TODO: this function is copied from MeasurementTool class, to be generalized?
    def send_callback(self, action: Action, cb_data: dict, raiseException: bool = True):
        """
        Notify the caller about measurement progress.

        If the registered callback returns ``False``, the scan is aborted by
        raising ``KeyboardInterrupt`` when ``raiseException`` is ``True``.
        The measurement tool adds its mode and source to ``cb_data`` before
        invoking the callback.
        Callback example:

        .. code-block:: python

            def callback(action: Action, data: dict):
                print(f"{action}, data:{data}")
                return True

            # Correct the orbit using the above callback
            sr.design.tool.orbit.correct(callback=callback)

        Parameters
        ----------
        action : Action
          Measurement lifecycle event.

        cb_data : dict
          Mutable event data passed to the callback.
        raiseException : bool, optional
          Whether a callback rejection should raise ``KeyboardInterrupt``.

        Returns
        -------
        bool
            Callback result, or ``True`` when no callback is registered.
        """
        ok = True
        if self._callback is not None:
            # Add source and peer
            cb_data["mode"] = self.attached_to()
            cb_data["source"] = self
            ok = self._callback(action, cb_data)
        if not ok and raiseException:
            # Abort, same as ctrl+C
            raise KeyboardInterrupt
        return ok
