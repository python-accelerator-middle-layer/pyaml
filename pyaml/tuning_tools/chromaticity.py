"""
Chromaticity correction and response-matrix tools.

The :class:`Chromaticity` tool reads measured chromaticity, computes sextupole
strength corrections from a response matrix, and applies those corrections to
an accelerator model or control-system interface.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from .. import PyAMLException
from ..validation import DynamicValidation, register_schema
from .chromaticity_monitor import ChromaticityMonitor
from .knobs import knobs_of
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

    Attributes
    ----------
    response_matrix
        Return the loaded chromaticity response matrix, if available.
    chromaticity_monitor
        Return the chromaticity monitor used for readback.
    sextupoles
        Return the sextupole array as configured.
    knobs
        Return the knobs of the sextupole array, one per power supply: a series
        is one knob, its serialized family. The correction writes the knobs.

    Methods
    -------
    load(load_path)
        Load a chromaticity response matrix and prepare its pseudoinverse.
    get()
        Return the requested horizontal and vertical chromaticity.
    readback()
        Measure and return the current horizontal and vertical chromaticity.
    set(chroma, iter=1, wait_time=0.0)
        Iteratively correct chromaticity to a requested setpoint.
    correct(dchroma)
        Calculate sextupole-strength changes for a chromaticity change.
    add(dchroma, wait_time=0.0)
        Apply a chromaticity correction relative to the current setpoint.

    Configuration
    -------------
    .. code-block:: yaml

        - type: pyaml.tuning_tools.chromaticity
          name: CHROMATICITY_CORRECTION
          sextu_array_name: SEXTUPOLES
          chromaticity_monitor_name: CHROMATICITY_MONITOR
          response_matrix: path/to/chromaticity_response.json
    """

    def __init__(
        self, name: str, sextu_array_name: str, chromaticity_monitor_name: str, response_matrix: str | ResponseMatrixData
    ):
        """
        Initialize a chromaticity adjustment tool.
        """
        super().__init__(name)
        self.sextu_array_name = sextu_array_name
        self._chromaticity_monitor_name = chromaticity_monitor_name
        self.response_matrix_file = response_matrix
        self._response_matrix = None
        self._response_data: ResponseMatrixData | None = None
        self._correctionmat = None
        self._knobs = None

        # If the configuration response matrix is a filename, load it
        if type(response_matrix) is str:
            try:
                response_matrix = ResponseMatrixData.load(response_matrix)
            except Exception as e:
                logger.warning(f"{str(e)}")
                response_matrix = None

        if response_matrix:
            self.__set_response_data(response_matrix)

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
        self.__set_response_data(ResponseMatrixData.load(load_path))

    def __set_response_data(self, data: ResponseMatrixData):
        """Keep the response matrix data, with its variable names, and invert the matrix."""
        self._response_data = data
        self._response_matrix = np.array(data.matrix)
        self._correctionmat = np.linalg.pinv(self._response_matrix)

    def post_init(self):
        """Warn when the loaded response matrix does not match the knobs, without preventing the loading."""
        try:
            self.__check_response_matrix()
        except PyAMLException as e:
            logger.warning(f"{e}")

    def __check_response_matrix(self):
        """Raise if the loaded response matrix does not match the knobs."""
        if self._response_data is None:
            return
        difference = self._response_data.check_variables(self.knobs.names())
        if difference is not None:
            raise PyAMLException(f"{self.get_name()}: {difference}, measure a new chromaticity response matrix")

    @property
    def chromaticity_monitor(self) -> "ChromaticityMonitor":
        """Return the chromaticity monitor used for readback."""
        self.check_peer()
        return self.peer.tool.get(self._chromaticity_monitor_name)

    @property
    def sextupoles(self) -> "MagnetArray":
        """Return the sextupole array used for correction."""
        self.check_peer()
        return self.peer.magnets.get(self.sextu_array_name)

    @property
    def knobs(self) -> "MagnetArray":
        """Return the knobs of the sextupole array, one per power supply, see :func:`~.knobs.knobs_of`."""
        if self._knobs is None:
            self._knobs = knobs_of(self.sextupoles)
        return self._knobs

    def get(self):
        """Return the requested dimensionless horizontal and vertical chromaticity."""
        return self._setpoint

    def readback(self):
        """Measure and return the current dimensionless horizontal and vertical chromaticity."""
        self.chromaticity_monitor.measure()
        return self.chromaticity_monitor.chromaticity.get()

    def set(self, chroma: np.array, iter: int = 1, wait_time: float = 0.0):
        """
        Iteratively correct chromaticity to a requested setpoint.

        Parameters
        ----------
        chroma : numpy.ndarray
            Target horizontal and vertical chromaticity values (dimensionless).
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
            Desired horizontal and vertical chromaticity change (dimensionless).

        Returns
        -------
        numpy.ndarray
            Strength change of each knob, obtained from the response-matrix
            pseudoinverse, in the configured sextupole strength units
            (typically ``m^-2``).

        Raises
        ------
        PyAMLException
            If no response matrix has been loaded or measured, or if it does
            not match the knobs.
        """
        if self._correctionmat is None:
            raise PyAMLException("Chromaticity.correct(): no matrix loaded or measured")
        self.__check_response_matrix()
        return np.matmul(self._correctionmat, dchroma)

    def add(self, dchroma: np.array, wait_time: float = 0.0):
        """
        Apply a chromaticity correction relative to the current setpoint.

        Parameters
        ----------
        dchroma : numpy.ndarray
            Horizontal and vertical chromaticity change to apply (dimensionless).
        wait_time : float
            Delay in seconds after changing sextupole strengths.
        """
        strengths = self.knobs.strengths.get()
        strengths += self.correct(dchroma)
        self.knobs.strengths.set(strengths)
        time.sleep(wait_time)
        self._setpoint += dchroma
