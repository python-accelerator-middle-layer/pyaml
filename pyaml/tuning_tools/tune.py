"""
Betatron-tune measurement and correction tools.

The :class:`Tune` tool reads horizontal and vertical betatron tune, computes
quadrupole-strength corrections from a response matrix, and applies those
corrections to the configured quadrupole array.
"""

import logging
from pathlib import Path
from time import sleep
from typing import TYPE_CHECKING

import numpy as np

from .. import PyAMLException
from .response_matrix_data import ResponseMatrixData
from .tuning_tool import TuningTool

if TYPE_CHECKING:
    from ..arrays.magnet_array import MagnetArray
    from ..diagnostics.tune_monitor import BetatronTuneMonitor

from ..validation import DynamicValidation, register_schema

logger = logging.getLogger(__name__)

# Define the main class name for this module
PYAMLCLASS = "Tune"


@register_schema
class Tune(TuningTool, DynamicValidation):
    """
    Adjust the horizontal and vertical betatron tunes.

    The tune correction is calculated from a response matrix describing the
    change in horizontal and vertical tune produced by changes in quadrupole
    strength. The pseudo-inverse of this matrix is used to convert a requested
    tune change into the corresponding quadrupole-strength changes.

    The response matrix may be supplied directly as a
    :class:`ResponseMatrixData` instance or loaded from a file. The tune is
    measured using the configured betatron tune monitor, while corrections are
    applied through the configured quadrupole array.

    Parameters
    ----------
    name : str
        Name of the tuning tool.
    quad_array_name : str
        Name of the quadrupole array used to adjust the tune.
    betatron_tune_name : str
        Name of the betatron tune monitor used to measure the horizontal and
        vertical tunes.
    response_matrix : str or ResponseMatrixData
        Tune response matrix or path to a file containing the response matrix.
        The matrix is expected to have one row for each tune plane and one
        column for each quadrupole.

    Attributes
    ----------
    quad_array_name : str
        Name of the configured quadrupole array.
    betatron_tune_name : str
        Name of the configured betatron tune monitor.
    response_matrix : ResponseMatrixData or None
        Loaded tune response matrix.
    """

    def __init__(
        self,
        name: str,
        quad_array_name: str,
        betatron_tune_name: str,
        response_matrix: str | ResponseMatrixData,
    ):
        """
        Initialize a betatron-tune correction tool.

        Parameters
        ----------
        name : str
            Name of the tuning tool.
        quad_array_name : str
            Name of the quadrupole array used for correction.
        betatron_tune_name : str
            Name of the betatron-tune monitor used for readback.
        response_matrix : str | ResponseMatrixData
            Tune response matrix or path to a serialized response matrix.
        """
        super().__init__(name)

        self.quad_array_name = quad_array_name
        self.betatron_tune_name = betatron_tune_name
        self._response_matrix = response_matrix
        self._correctionmat = None

        # If the configuration response matrix is a filename, load it
        if type(self._response_matrix) is str:
            try:
                self._response_matrix = ResponseMatrixData.load(self._response_matrix)
            except Exception as e:
                logger.warning(f"{str(e)}")
                self._response_matrix = None

        # Invert matrix
        if self._response_matrix:
            self._response_matrix = np.array(self._response_matrix.matrix)
            self._correctionmat = np.linalg.pinv(self._response_matrix)

        # TODO: Initialise first setpoint
        self._setpoint = np.array([np.nan, np.nan])

    def load(self, load_path: Path):
        """
        Load a tune response matrix and prepare its pseudoinverse.

        Parameters
        ----------
        load_path : Path
            Path to the serialized :class:`~.ResponseMatrixData` file.
        """
        self._response_matrix = ResponseMatrixData.load(load_path)
        self._response_matrix = np.array(self._response_matrix.matrix)
        self._correctionmat = np.linalg.pinv(self._response_matrix)

    @property
    def response_matrix(self) -> ResponseMatrixData | None:
        """Return the loaded tune response matrix, if available."""
        return self._response_matrix

    @property
    def _tm(self) -> "BetatronTuneMonitor":
        """Return the betatron tune monitor."""
        self.check_peer()
        return self.peer.get_betatron_tune_monitor(self.betatron_tune_name)

    @property
    def _quads(self) -> "MagnetArray":
        """Return the quadrupole array."""
        self.check_peer()
        return self.peer.magnets.get(self.quad_array_name)

    def get(self):
        """Return the requested horizontal and vertical tune setpoint."""
        return self._setpoint

    def readback(self):
        """Return the current horizontal and vertical betatron tune."""
        self.check_peer()
        return self._tm.tune.get()

    def set(self, tune: np.array, iter: int = 1, wait_time: float = 0.0):
        """
        Iteratively correct the betatron tune to a requested setpoint.

        Parameters
        ----------
        tune : np.array
            Target horizontal and vertical tune values.
        iter : int
            Number of correction iterations.
        wait_time : float
            Delay in seconds between correction iterations.
        """
        if np.shape(tune) != (2,):
            raise PyAMLException("Tune.add(): invalid input tune dimension, (2,) expected")
        for i in range(iter):
            diff_tune = tune - self.readback()
            if i == iter:
                wait_time = 0  # do not wait on last iteration
            self.add(diff_tune, wait_time)
        self._setpoint = np.array(tune)

    def correct(self, dtune: np.array) -> np.array:
        """
        Calculate quadrupole-strength changes for a tune change.

        Parameters
        ----------
        dtune : np.array
            Desired horizontal and vertical tune change.

        Returns
        -------
        numpy.ndarray
            Quadrupole-strength changes calculated from the response-matrix
            pseudoinverse.

        Raises
        ------
        PyAMLException
            If no response matrix has been loaded.
        """
        if self._correctionmat is None:
            raise PyAMLException("Tune.correct(): no matrix loaded or measured")
        return np.matmul(self._correctionmat, dtune)

    def add(self, dtune: np.array, wait_time: float = 0.0):
        """
        Apply a tune correction relative to the current setpoint.

        Parameters
        ----------
        dtune : np.array
            Horizontal and vertical tune change to apply.
        wait_time : float
            Delay in seconds after changing quadrupole strengths.
        """
        if np.shape(dtune) != (2,):
            raise PyAMLException("Tune.add(): invalid input dtune dimension, (2,) expected")
        strengths = self._quads.strengths.get()
        strengths += self.correct(dtune)
        self._quads.strengths.set(strengths)
        sleep(wait_time)
        self._setpoint += dtune
