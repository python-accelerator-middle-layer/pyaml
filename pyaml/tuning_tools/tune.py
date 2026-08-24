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
    """Adjust the horizontal and vertical betatron tunes.

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
        Dynamically loads a response matrix.

        Parameters
        ----------
        load_path : Path
            Filename of the :class:`~.ResponseMatrixData` to load

        """
        self._response_matrix = ResponseMatrixData.load(load_path)
        self._response_matrix = np.array(self._response_matrix.matrix)
        self._correctionmat = np.linalg.pinv(self._response_matrix)

    @property
    def response_matrix(self) -> ResponseMatrixData | None:
        """
        Return the response matrix if it has been loaded None otherwise
        """
        return self._response_matrix

    @property
    def _tm(self) -> "BetatronTuneMonitor":
        self.check_peer()
        return self.peer.get_betatron_tune_monitor(self.betatron_tune_name)

    @property
    def _quads(self) -> "MagnetArray":
        self.check_peer()
        return self.peer.magnets.get(self.quad_array_name)

    def get(self):
        """
        Return the betatron tune setpoint
        """
        return self._setpoint

    def readback(self):
        """
        Return the betatron tune measurement
        """
        self.check_peer()
        return self._tm.tune.get()

    def set(self, tune: np.array, iter: int = 1, wait_time: float = 0.0):
        """
        Sets the tune

        Parameters
        ----------
        tune : np.array
            Tune setpoint
        iter_nb : int
            Number of iteration
        wait_time : float
            Time to wait in second between 2 iterations
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
        Return delta strengths for tune correction

        Parameters
        ----------
        dtune : np.array
            Delta tune
        """
        if self._correctionmat is None:
            raise PyAMLException("Tune.correct(): no matrix loaded or measured")
        return np.matmul(self._correctionmat, dtune)

    def add(self, dtune: np.array, wait_time: float = 0.0):
        """
        Add delta tune to the tune

        Parameters
        ----------
        dtune : np.array
            Delta tune
        iter_nb: int
        wait_time: float
        """
        if np.shape(dtune) != (2,):
            raise PyAMLException("Tune.add(): invalid input dtune dimension, (2,) expected")
        strengths = self._quads.strengths.get()
        strengths += self.correct(dtune)
        self._quads.strengths.set(strengths)
        sleep(wait_time)
        self._setpoint += dtune
