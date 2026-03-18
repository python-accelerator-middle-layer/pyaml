from pathlib import Path
from typing import TYPE_CHECKING

from .. import PyAMLException
from ..common.element import ElementConfigModel
from .response_matrix_data import ResponseMatrixData
from .tuning_tool import TuningTool

if TYPE_CHECKING:
    from ..arrays.magnet_array import MagnetArray
    from ..diagnostics.tune_monitor import BetatronTuneMonitor

try:
    from typing import Self  # Python 3.11+
except ImportError:
    from typing_extensions import Self  # Python 3.10 and earlier
import logging
import time

import numpy as np

logger = logging.getLogger(__name__)

# Define the main class name for this module
PYAMLCLASS = "Tune"


class ConfigModel(ElementConfigModel):
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
    response_matrix : str | ResponseMatrixData
        filename or data of the tune response matrix
    """

    quad_array_name: str
    betatron_tune_name: str
    response_matrix: str | ResponseMatrixData


class Tune(TuningTool):
    """
    Class providing tune adjustment tool
    """

    def __init__(self, cfg: ConfigModel):
        """
        Construct a Tune adjustment object.

        Parameters
        ----------
        cfg : ConfigModel
            Configuration for the tune adjustment.
        """
        super().__init__(cfg.name)
        self._cfg = cfg
        self._response_matrix = None
        self._correctionmat = None

        # If the configuration response matrix is a filename, load it
        if type(cfg.response_matrix) is str:
            try:
                cfg.response_matrix = ResponseMatrixData.load(cfg.response_matrix)
            except Exception as e:
                logger.warning(f"{str(e)}")
                cfg.response_matrix = None

        # Invert matrix
        if cfg.response_matrix:
            self._response_matrix = np.array(cfg.response_matrix._cfg.matrix)
            self._correctionmat = np.linalg.pinv(self._response_matrix)

        # TODO: Initialise first setpoint
        self._setpoint = np.array([np.nan, np.nan])

    def load(self, load_path: Path):
        self._cfg.response_matrix = ResponseMatrixData.load(load_path)
        self._response_matrix = np.array(self._cfg.response_matrix._cfg.matrix)
        self._correctionmat = np.linalg.pinv(self._response_matrix)

    @property
    def _tm(self) -> "BetatronTuneMonitor":
        self.check_peer()
        return self._peer.get_betatron_tune_monitor(self._cfg.betatron_tune_name)

    @property
    def _quads(self) -> "MagnetArray":
        self.check_peer()
        return self._peer.get_magnets(self._cfg.quad_array_name)

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
        time.sleep(wait_time)
        self._setpoint += dtune
