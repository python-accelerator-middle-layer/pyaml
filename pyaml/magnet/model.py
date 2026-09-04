"""Abstract interfaces for magnet conversion models.

The :class:`MagnetModel` contract covers conversion between physical strengths
and hardware setpoints, unit metadata, device names, and magnetic rigidity.
"""

from abc import ABCMeta, abstractmethod

import numpy as np
import numpy.typing as npt


class MagnetModel(metaclass=ABCMeta):
    """
    Define the interface for magnet strength and hardware conversion.

    Concrete models implement the relationship between accelerator physics
    strengths and power-supply values for one or more magnet functions.
    """

    @abstractmethod
    def compute_hardware_values(self, strengths: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        """
        Compute hardware value(s) from magnet strength(s)

        Parameters
        ----------
        strengths : npt.NDArray[np.float64]
            Array of strengths. For a single multipole,
            strengths is an array of 1 item.

        Returns
        -------
        npt.NDArray[np.float64]
            Array of hardware values (i.e. currents or voltages).
        """
        pass

    @abstractmethod
    def compute_strengths(self, hardware_values: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        """
        Compute magnet strength(s) from hardware value(s)

        Parameters
        ----------
        hardware_values : npt.NDArray[np.float64]
            Array of hardware values (i.e. currents or voltages)

        Returns
        -------
        npt.NDArray[np.float64]
            Array of strengths. For a single multipole,
            returns an array of 1 item
        """
        pass

    @abstractmethod
    def get_strength_units(self) -> list[str]:
        """
        Get strength units

        Returns
        -------
        list[str]
            Array of strength units. For a single multipole,
            returns a list of 1 item
        """
        pass

    @abstractmethod
    def get_device_names(self) -> list[str | None]:
        """
        Get device names

        Returns
        -------
            list[str | None]
            Array of associated device names.
        """
        pass

    @abstractmethod
    def set_magnet_rigidity(self, brho: np.double):
        """
        Set magnet rigidity

        Parameters
        ----------
        brho: np.double
            Magnet rigidity used to calculate power supply setpoints
        """
        pass

    def has_hardware(self) -> bool:
        """
        Tells if the model allows to work in hardware unit.

        Returns
        ----------
        bool
            True if the model supports hardware unit
        """
        return True

    def has_physics(self) -> bool:
        """
        Tells if the model allows to work in physics unit.

        Returns
        ----------
        bool
            True if the model supports physics unit
        """
        return True
