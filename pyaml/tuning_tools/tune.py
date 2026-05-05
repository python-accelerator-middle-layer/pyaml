import logging
from pathlib import Path
from time import sleep
from typing import TYPE_CHECKING

import numpy as np

try:
    from typing import Self  # Python 3.11+
except ImportError:
    from typing_extensions import Self  # Python 3.10 and earlier

from .. import PyAMLException
from ..common.element import ElementConfigModel
from .response_matrix_data import ResponseMatrixData, ResponseMatrixDataSchema
from .tuning_tool import TuningTool

if TYPE_CHECKING:
    from ..arrays.magnet_array import MagnetArray
    from ..diagnostics.tune_monitor import BetatronTuneMonitor

logger = logging.getLogger(__name__)


class TuneSchema(ElementConfigModel):
    """
    Configuration model for Tune

    Parameters
    ----------
    quad_array_name : str
        Array name of quad used to adjust the tune
    betatron_tune_name : str
        Name of the diagnostic pyaml device for measuring the tune
    quad_delta : float
        Delta strength used to get the response matrix

    """

    quad_array_name: str
    betatron_tune_name: str
    response_matrix: str | ResponseMatrixDataSchema


class Tune(TuningTool):
    """
    Class providing tune adjustment tool
    """

    def __init__(
        self,
        name: str,
        quad_array_name: str,
        betatron_tune_name: str,
        response_matrix: str | ResponseMatrixData,
    ):
        """
        Construct a Tune adjustment object.

        """
        super().__init__(name)
        self._quad_array_name = quad_array_name
        self._betatron_tune_name = betatron_tune_name
        self._response_matrix = None
        self._correctionmat = None

        # If the configuration response matrix is a filename, load it
        if type(response_matrix) is str:
            try:
                response_matrix = ResponseMatrixData.load(response_matrix)
            except Exception as e:
                logger.warning(f"{str(e)}")
                response_matrix = None

        # Invert matrix
        if response_matrix:
            self._response_matrix = np.array(response_matrix._matrix)
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
        self._response_matrix = np.array(self._response_matrix._matrix)
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
        return self.peer.get_betatron_tune_monitor(self._betatron_tune_name)

    @property
    def _quads(self) -> "MagnetArray":
        self.check_peer()
        return self.peer.get_magnets(self._quad_array_name)

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
        strengths = self._quads.strengths.get()
        strengths += self.correct(dtune)
        self._quads.strengths.set(strengths)
        sleep(wait_time)
        self._setpoint += dtune
