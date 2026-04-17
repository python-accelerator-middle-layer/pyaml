from abc import ABCMeta, abstractmethod

from ..common.abstract import ReadFloatArray


class ABetatronTuneMonitor(metaclass=ABCMeta):
    """
    Abstract class providing access to a betatron tune monitor
    """

    @property
    @abstractmethod
    def tune(self) -> ReadFloatArray:
        """
        Returns the tune fractionnal part
        """
        ...

    @property
    @abstractmethod
    def frequency(self) -> ReadFloatArray:
        """
        Returns the tune in frequency
        """
        ...
