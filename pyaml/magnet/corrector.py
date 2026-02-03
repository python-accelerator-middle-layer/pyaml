import numpy as np

from ..common import abstract
from .magnet import Magnet


class RWCorrectorAngle(abstract.ReadWriteFloatScalar):
    """
    Set the angle of a horizontal or vertical corrector.
    KickAngle sign convention is defined the a global PyAML constant
    (see pyaml.common.constant.HORIZONATL_KICK_SIGN).
    To change the convention, you have execute the code below prior to everything:
    import pyaml.common.constants
    pyaml.common.constants.HORIZONTAL_KICK_SIGN = -1.0
    """

    def __init__(self, corr: Magnet):
        self._mag = corr

    def get(self) -> float:
        """
        Get the corrector kick angle.

        Returns
        -------
        float
            Kick angle in radians
        """
        return np.arctan(self._mag.strength.get())

    def set(self, value: float):
        """
        Set the corrector kick angle.

        Parameters
        ----------
        value : float
            Kick angle to set in radians
        """
        self._mag.strength.set(np.tan(value))

    def set_and_wait(self, value: float):
        """
        Set the kick angle and wait for it to reach the setpoint.

        Parameters
        ----------
        value : float
            Target kick angle in radians

        Raises
        ------
        NotImplementedError
            This method is not yet implemented
        """
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        """
        Get the unit for the kick angle.

        Returns
        -------
        str
            Unit string, always 'rad' for radians
        """
        return "rad"
