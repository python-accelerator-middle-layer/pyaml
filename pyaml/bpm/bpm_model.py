from abc import ABCMeta, abstractmethod


class BPMModel(metaclass=ABCMeta):
    """
    Abstract class providing interface to accessing BPM positions, offsets,
    tilts.
    """

    @abstractmethod
    def get_pos_devices(self) -> list[str]:
        """
        Get device handles used for position reading

        Returns
        -------
        list[DeviceAccess]
            h and v position devices
        """
        pass

    @abstractmethod
    def get_tilt_device(self) -> str | None:
        """
        Get device handle used for tilt access

        Returns
        -------
        list[DeviceAccess]
            tilt device
        """
        pass

    @abstractmethod
    def get_offset_devices(self) -> list[str | None]:
        """
        Get device handles used for offset access

        Returns
        -------
        list[DeviceAccess]
            h and v offset devices
        """
        pass
