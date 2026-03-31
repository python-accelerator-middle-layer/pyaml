from pathlib import Path
from typing import TYPE_CHECKING

from .. import PyAMLException
from ..common.element import ElementConfigModel
from ..diagnostics.chromaticity_monitor import ChomaticityMonitor
from .response_matrix_data import ResponseMatrixData
from .tuning_tool import TuningTool

if TYPE_CHECKING:
    from ..arrays.magnet_array import MagnetArray

try:
    from typing import Self  # Python 3.11+
except ImportError:
    from typing_extensions import Self  # Python 3.10 and earlier
import logging
import time

import numpy as np

logger = logging.getLogger(__name__)

# Define the main class name for this module
PYAMLCLASS = "Chromaticity"


class ConfigModel(ElementConfigModel):
    """
    Configuration model for Tune

    Parameters
    ----------
    sextu_array_name : str
        Array name of sextu used to adjust the chromaticity
    chromaticty_monitor_name : str
        Name of the diagnostic pyaml device for measuring the chromaticity
    response_matrix : str | ResponseMatrixData
        filename or data of the chromaticity response matrix
    """

    sextu_array_name: str
    chromaticty_monitor_name: str
    response_matrix: str | ResponseMatrixData


class Chromaticity(TuningTool):
    """
    Class providing chromaticity adjustment tool
    """

    def __init__(self, cfg: ConfigModel):
        """
        Construct a chromaticity adjustment object.

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
        """
        Dyanmically loads a response matrix.

        Parameters
        ----------
        load_path : Path
            Filename of the :class:`~.ResponseMatrixData` to load
        """
        self._cfg.response_matrix = ResponseMatrixData.load(load_path)
        self._response_matrix = np.array(self._cfg.response_matrix._cfg.matrix)
        self._correctionmat = np.linalg.pinv(self._response_matrix)

    @property
    def _cm(self) -> "ChomaticityMonitor":
        self.check_peer()
        return self._peer.get_chromaticity_monitor(self._cfg.chromaticty_monitor_name)

    @property
    def _sextu(self) -> "MagnetArray":
        self.check_peer()
        return self._peer.get_magnets(self._cfg.sextu_array_name)

    def get(self):
        """
        Return the chromaticity setpoint
        """
        return self._setpoint

    def readback(self):
        """
        Launch a chromaticty scan and returns the measured chromaticity.
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
