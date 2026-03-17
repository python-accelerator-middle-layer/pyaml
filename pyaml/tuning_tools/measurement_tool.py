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

    @abstractmethod
    def measure(self):
        """
        Launch measurement
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

    def send_callback(self, action: Action, callback: Callable, cb_data: dict) -> bool:
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

        callback: Callable
          Callback to be executed

        cb_data: dict
          Callback data
        """
        if callback is not None:
            # Add source
            cb_data["source"] = self.__class__.__name__
            return callback(action, cb_data)
        return True

    def attach(self, peer: "ElementHolder") -> Self:
        """
        Create a new reference to attach this measurement tool object to a simulator
        or a control system.
        """
        obj = self.__class__(self._cfg)
        obj._peer = peer
        return obj
