"""
Base classes for accelerator measurement tools.

Measurement tools perform scans or response measurements, report progress
through callbacks, and retain their latest results for inspection or export.
"""

import copy
import logging
from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Self

from ..common.constants import Action
from ..common.element import Element
from ..common.exception import PyAMLException

if TYPE_CHECKING:
    from ..common.holders.element_holder import ElementHolder

logger = logging.getLogger(__name__)


class MeasurementTool(Element, metaclass=ABCMeta):
    """
    Base class for response-matrix measurements and accelerator scans.

    Subclasses implement :meth:`measure` and may use the shared callback,
    result-storage, attachment, and persistence helpers provided here.

    Parameters
    ----------
    name : object
        Name of the measurement tool.

    Attributes
    ----------
    latest_measurement
        Data produced by the last measurement, or ``None`` before the first one.

    Methods
    -------
    measure()
        Run the measurement implemented by a subclass.
    get()
        Return the most recently stored measurement data.
    save(save_path, with_type='json')
        Save the latest measurement data to disk.
    send_callback(action, cb_data, raiseException=True)
        Notify the caller about measurement progress.
    attach(peer)
        Return a copy attached to an element holder.
    """

    def __init__(self, name):
        """
        Initialize a measurement tool.
        """
        super().__init__(name)
        self._latest_measurement: dict = None
        self._peer: "ElementHolder" = None  # Peer: ControlSystem or Simulator
        self._callback: Callable = None

    def _init_measure(self, measurement_type: str | None = None):
        # Initialize measurement data
        # type is used there to be able to reload a measurement, typically a reponse matrix, using the PyAML factory.
        """
        Reset the latest measurement before starting a new scan.

        Parameters
        ----------
        measurement_type : str | None
            Optional fully qualified configuration type to store with the
            measurement data.
        """
        self._latest_measurement = {}
        if measurement_type is not None:
            self._latest_measurement["type"] = measurement_type

    @abstractmethod
    def measure(self) -> bool:
        """
        Run the measurement implemented by a subclass.

        Returns
        -------
        bool
            ``True`` when the measurement completes; ``False`` when it is
            aborted according to the subclass contract.
        """
        raise NotImplementedError()

    @property
    def latest_measurement(self) -> dict:
        """
        Return the most recently stored measurement data.

        Returns
        -------
        dict
            Measurement data, or ``None`` before the first measurement.
        """
        return self._latest_measurement

    def get(self) -> dict:
        """
        Return the most recently stored measurement data.

        Returns
        -------
        dict
            Measurement data, or ``None`` before the first measurement.
        """
        return self._latest_measurement

    def save(self, save_path: Path, with_type: str = "json"):
        """
        Save the latest measurement data to disk.

        Parameters
        ----------
        save_path : Path
            Destination filename.
        with_type : str
            Serialization format: ``"json"``, ``"yaml"``, or ``"npz"``.

        Raises
        ------
        PyAMLException
            If ``with_type`` is not a supported serialization format.
        """
        if with_type == "json":
            import json

            data = self.latest_measurement
            json.dump(data, open(save_path, "w"), indent=4)
        elif with_type == "yaml":
            import yaml

            data = self.latest_measurement
            yaml.safe_dump(data, open(save_path, "w"))
        elif with_type == "npz":
            import numpy as np

            data = self.latest_measurement
            np.savez(save_path.resolve(), **data)
        else:
            raise PyAMLException(f"ERROR: Unknown file type to save as: {with_type}.")

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

            # Measure a tune response matrix using the above callback
            sr.design.trm.measure(callback=callback)

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
            cb_data["mode"] = f"{self.attached_to()}"
            cb_data["source"] = self
            ok = self._callback(action, cb_data)
        if not ok and raiseException:
            # Abort, same as ctrl+C
            raise KeyboardInterrupt
        return ok

    def _register_callback(self, callback: Callable):
        """
        Register a progress callback for the next measurement.

        Parameters
        ----------
        callback : Callable
            Callable receiving an :class:`Action` and event-data dictionary.
        """
        self._callback = callback

    def attach(self, peer: "ElementHolder") -> Self:
        """
        Return a copy attached to an element holder.

        A shallow copy is created so the configured measurement tool remains
        reusable. Subclasses can rebind internal handles in :meth:`_after_attach`.

        Parameters
        ----------
        peer : 'ElementHolder'
            Accelerator, simulator, or control-system element holder.

        Returns
        -------
        Self
            Attached copy of this measurement tool.
        """
        obj = copy.copy(self)
        obj._after_attach()
        obj._peer = peer
        return obj

    def _after_attach(self) -> None:
        """Hook for subclasses to rebind internal references after attach."""
        pass
