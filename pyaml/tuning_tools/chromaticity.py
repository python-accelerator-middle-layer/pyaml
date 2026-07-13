from pathlib import Path
from typing import TYPE_CHECKING

from .. import PyAMLException
from ..validation import DynamicValidation, register_schema
from .chromaticity_monitor import ChomaticityMonitor
from .response_matrix_data import ResponseMatrixData
from .tuning_tool import TuningTool

if TYPE_CHECKING:
    from ..arrays.magnet_array import MagnetArray

import logging
import time

import numpy as np

logger = logging.getLogger(__name__)

# Define the main class name for this module
PYAMLCLASS = "Chromaticity"


@register_schema
class Chromaticity(TuningTool, DynamicValidation):
    """
    Class providing chromaticity adjustment tool
    """

    def __init__(
        self, name: str, sextu_array_name: str, chromaticity_monitor_name: str, response_matrix: str | ResponseMatrixData
    ):
        """
        Initialize a chromaticity adjustment tool.

        Parameters
        ----------
        name : str
            Name of the tuning tool.
        sextu_array_name : str
            Name of the sextupole array used to adjust the chromaticity.
        chromaticity_monitor_name : str
            Name of the chromaticity monitor used for readback.
        response_matrix : str | ResponseMatrixData
            Chromaticity response matrix or path to a saved response matrix file.
        """
        super().__init__(name)
        self.sextu_array_name = sextu_array_name
        self._chromaticity_monitor_name = chromaticity_monitor_name
        self.response_matrix_file = response_matrix
        self._response_matrix = None
        self._correctionmat = None

        # If the configuration response matrix is a filename, load it
        if type(self.response_matrix_file) is str:
            try:
                self._response_matrix = ResponseMatrixData.load(self.response_matrix_file)
            except Exception as e:
                logger.warning(f"{str(e)}")
                self._response_matrix = None

        # Invert matrix
        if self._response_matrix:
            self._response_matrix = np.array(self._response_matrix._cfg.matrix)
            self._correctionmat = np.linalg.pinv(self._response_matrix)

        # TODO: Initialise first setpoint
        self._setpoint = np.array([np.nan, np.nan])

    @property
    def response_matrix(self) -> ResponseMatrixData | None:
        """
        Return the response matrix if it has been loaded None otherwise
        """
        return self._response_matrix

    def load(self, load_path: Path):
        """
        Dynamically loads a response matrix.

        Parameters
        ----------
        load_path : Path
            Filename of the :class:`~.ResponseMatrixData` to load
        """
        self._response_matrix = ResponseMatrixData.load(load_path)
        self._response_matrix = np.array(self._response_matrix._cfg.matrix)
        self._correctionmat = np.linalg.pinv(self._response_matrix)

    @property
    def _cm(self) -> "ChomaticityMonitor":
        self.check_peer()
        return self.peer.get_chromaticity_monitor(self._chromaticity_monitor_name)

    @property
    def _sextu(self) -> "MagnetArray":
        self.check_peer()
        return self.peer.get_magnets(self.sextu_array_name)

    def get(self):
        """
        Return the chromaticity setpoint
        """
        return self._setpoint

    def readback(self):
        """
        Launch a chromaticity scan and returns the measured chromaticity.
        """
        self._cm.measure()
        return self._cm.chromaticity.get()

    def set(self, chroma: np.array, iter: int = 1, wait_time: float = 0.0):
        """
        Sets the chromaticity

        Parameters
        ----------
        chromaticity : np.array
            Chromaticity setpoint
        iter_nb : int
            Number of iteration
        wait_time : float
            Time to wait in second between 2 iterations
        """
        for i in range(iter):
            diff_chroma = chroma - self.readback()
            if i == iter:
                wait_time = 0  # do not wait on last iteration
            self.add(diff_chroma, wait_time)
        self._setpoint = np.array(chroma)

    def correct(self, dchroma: np.array) -> np.array:
        """
        Return delta strengths for chromaticity correction

        Parameters
        ----------
        dchroma : np.array
            Delta chroma
        """
        if self._correctionmat is None:
            raise PyAMLException("Chromaticity.correct(): no matrix loaded or measured")
        return np.matmul(self._correctionmat, dchroma)

    def add(self, dchroma: np.array, wait_time: float = 0.0):
        """
        Add delta chromaticity to the actual chromaticity

        Parameters
        ----------
        dchroma : np.array
            Delta tune
        iter_nb: int
        wait_time: float
        """
        strengths = self._sextu.strengths.get()
        strengths += self.correct(dchroma)
        self._sextu.strengths.set(strengths)
        time.sleep(wait_time)
        self._setpoint += dchroma
