"""Chromaticity correction and response-matrix tools.

The :class:`Chromaticity` tool reads measured chromaticity, computes sextupole
strength corrections from a response matrix, and applies those corrections to
an accelerator model or control-system interface.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from .. import PyAMLException
from ..validation import DynamicValidation, register_schema
from .chromaticity_monitor import ChromaticityMonitor
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
    Adjust horizontal and vertical chromaticity with sextupole strengths.

    A response matrix maps sextupole-strength changes to chromaticity changes.
    Its pseudoinverse is used to calculate the strength correction required for
    a requested chromaticity change.
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
            self._response_matrix = np.array(self._response_matrix.matrix)
            self._correctionmat = np.linalg.pinv(self._response_matrix)

        # TODO: Initialise first setpoint
        self._setpoint = np.array([np.nan, np.nan])

    @property
    def response_matrix(self) -> ResponseMatrixData | None:
        """Return the loaded chromaticity response matrix, if available."""
        return self._response_matrix

    def load(self, load_path: Path):
        """
        Load a chromaticity response matrix and prepare its pseudoinverse.

        Parameters
        ----------
        load_path : Path
            Path to the serialized :class:`~.ResponseMatrixData` file.
        """
        self._response_matrix = ResponseMatrixData.load(load_path)
        self._response_matrix = np.array(self._response_matrix.matrix)
        self._correctionmat = np.linalg.pinv(self._response_matrix)

    @property
    def _cm(self) -> "ChromaticityMonitor":
        """Return the chromaticity monitor."""
        self.check_peer()
        return self.peer.get_chromaticity_monitor(self._chromaticity_monitor_name)

    @property
    def _sextu(self) -> "MagnetArray":
        """Return the sextupole array."""
        self.check_peer()
        return self.peer.magnets.get(self.sextu_array_name)

    def get(self):
        """Return the requested horizontal and vertical chromaticity."""
        return self._setpoint

    def readback(self):
        """Measure and return the current horizontal and vertical chromaticity."""
        self._cm.measure()
        return self._cm.chromaticity.get()

    def set(self, chroma: np.array, iter: int = 1, wait_time: float = 0.0):
        """
        Iteratively correct chromaticity to a requested setpoint.

        Parameters
        ----------
        chroma : numpy.ndarray
            Target horizontal and vertical chromaticity values.
        iter : int
            Number of correction iterations.
        wait_time : float
            Delay in seconds between correction iterations.
        """
        for i in range(iter):
            diff_chroma = chroma - self.readback()
            if i == iter:
                wait_time = 0  # do not wait on last iteration
            self.add(diff_chroma, wait_time)
        self._setpoint = np.array(chroma)

    def correct(self, dchroma: np.array) -> np.array:
        """
        Calculate sextupole-strength changes for a chromaticity change.

        Parameters
        ----------
        dchroma : numpy.ndarray
            Desired horizontal and vertical chromaticity change.

        Returns
        -------
        numpy.ndarray
            Sextupole-strength changes obtained from the response-matrix
            pseudoinverse.

        Raises
        ------
        PyAMLException
            If no response matrix has been loaded or measured.
        """
        if self._correctionmat is None:
            raise PyAMLException("Chromaticity.correct(): no matrix loaded or measured")
        return np.matmul(self._correctionmat, dchroma)

    def add(self, dchroma: np.array, wait_time: float = 0.0):
        """
        Apply a chromaticity correction relative to the current setpoint.

        Parameters
        ----------
        dchroma : numpy.ndarray
            Horizontal and vertical chromaticity change to apply.
        wait_time : float
            Delay in seconds after changing sextupole strengths.
        """
        strengths = self._sextu.strengths.get()
        strengths += self.correct(dchroma)
        self._sextu.strengths.set(strengths)
        time.sleep(wait_time)
        self._setpoint += dchroma
