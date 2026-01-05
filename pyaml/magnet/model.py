from abc import ABCMeta, abstractmethod

import numpy as np
import numpy.typing as npt

from ..control.deviceaccess import DeviceAccess


class MagnetModel(metaclass=ABCMeta):
    """
    Abstract class providing strength to coil current conversion
    and access to underlying power supplies
    """

    @abstractmethod
    def compute_hardware_values(
        self, strengths: npt.NDArray[np.float64]
    ) -> npt.NDArray[np.float64]:
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
    def compute_strengths(
        self, hardware_values: npt.NDArray[np.float64]
    ) -> npt.NDArray[np.float64]:
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
    def get_hardware_units(self) -> list[str]:
        """
        Get hardware units

        Returns
        -------
        list[str]
            Array of hardware units. For a single multipole,
            returns a list of 1 item
        """
        pass

    @abstractmethod
    def get_devices(self) -> list[DeviceAccess | None]:
        """
        Get device handles

        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAcess
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
