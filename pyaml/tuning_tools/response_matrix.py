import logging
from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Self

from ..common.element import Element
from ..common.element_holder import ElementHolder
from ..common.exception import PyAMLException
from .response_matrix_data import ResponseMatrixData

logger = logging.getLogger(__name__)


class ResponseMatrix(Element, metaclass=ABCMeta):
    """
    Base class for response matrix measurement
    """

    def __init__(self, name):
        super().__init__(name)
        self.latest_measurement: ResponseMatrixData = None

    @abstractmethod
    def measure(self):
        """
        Measure response matrix
        """
        raise NotImplementedError()

    def get(self):
        """
        Measure tune response matrix

        Returns
        -------
        ResponseMatrixData
            Return latest measurement or None
        """
        return self.latest_measurement

    # TDODO: Abstrat this method
    def load(self, load_path: Path):
        """
        Load response matrix

        Parameters
        ----------
        load_path: Path
            Matrix filename
        """
        raise NotImplementedError()

    def save(self, save_path: Path, with_type: str = "json"):
        """
        Save response matrix

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

    def attach(self, peer: "ElementHolder") -> Self:
        """
        Create a new reference to attach this ResponseMatrix object to a simulator
        or a control system.
        """
        obj = self.__class__(self._cfg)
        obj._peer = peer
        return obj
