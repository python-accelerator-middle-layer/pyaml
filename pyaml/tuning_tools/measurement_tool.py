import logging
from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Self

from ..common.constants import Action
from ..common.element import Element
from ..common.exception import PyAMLException

if TYPE_CHECKING:
    from ..common.element_holder import ElementHolder

logger = logging.getLogger(__name__)


class MeasurementTool(Element, metaclass=ABCMeta):
    """
    Base class for measurement tool such as reponse matrix measurement or other scans.
    """

    def __init__(self, name):
        super().__init__(name)
        self.latest_measurement: dict = None
        self._peer: "ElementHolder" = None  # Peer: ControlSystem or Simulator
        self._callback: Callable = None

    @abstractmethod
    def measure(self) -> bool:
        """
        Launch measurement
        Returns
        -------
        bool
            True if the process has been aborted
        """
        raise NotImplementedError()

    def get(self) -> dict:
        """
        Return last measurement data

        Returns
        -------
        ResponseMatrixData
            Return latest measurement or None
        """
        return self.latest_measurement

    # TODO: Abstract this method
    def load(self, load_path: Path):
        """
        Load measurement data

        Parameters
        ----------
        load_path: Path
            Matrix filename
        """
        raise NotImplementedError()

    def save(self, save_path: Path, with_type: str = "json"):
        """
        Save measurement data

        Parameters
        ----------
        save_path: Path
            Matrix filename
        with_type: str
            File type (json,yaml,npz)
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
        Send callback from this Measurement tool to the caller.
        If the callback returns False, the scan is aborted and actuators are restored to their orignal values.
        Callback example:

        .. code-block:: python

            def callback(action: Action, data: dict):
                print(f"{action}, data:{data}")
                return True

            # Measure a tune response matrix using the above callback
            sr.design.trm.measure(callback=callback)

        Parameters
        ----------
        action: Action
          See :py:class:`pyaml.common.constants.Action`

        cb_data: dict
          Callback data
        """
        ok = True
        if self._callback is not None:
            # Add source
            cb_data["mode"] = f"{self.get_peer()}"
            cb_data["source_name"] = f"{self.get_name()}"
            ok = self._callback(action, cb_data)
        if not ok and raiseException:
            # Abort, same as ctrl+C
            raise KeyboardInterrupt
        return ok

    def register_callback(self, callback: Callable):
        self._callback = callback

    def attach(self, peer: "ElementHolder") -> Self:
        """
        Create a new reference to attach this measurement tool object to a simulator
        or a control system.
        """
        obj = self.__class__(self._cfg)
        obj._peer = peer
        return obj
