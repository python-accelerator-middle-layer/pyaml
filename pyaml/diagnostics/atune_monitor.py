"""
Abstract interfaces for betatron tune monitors.

The interfaces describe the tune and frequency quantities exposed by concrete
betatron tune monitor implementations.
"""

from abc import ABCMeta, abstractmethod

from ..common.abstract import ReadFloatArray


class ABetatronTuneMonitor(metaclass=ABCMeta):
    """
    Define the read-only interface for a betatron tune monitor.

    Concrete monitors provide horizontal and vertical tune values and their
    corresponding frequencies.
    """

    @property
    @abstractmethod
    def tune(self) -> ReadFloatArray:
        """
        Return the fractional horizontal and vertical betatron tunes.

        Returns
        -------
        ReadFloatArray
            Readable array containing the horizontal and vertical tune
            fractions.
        """
        ...

    @property
    @abstractmethod
    def frequency(self) -> ReadFloatArray:
        """
        Return the horizontal and vertical tune frequencies.

        Returns
        -------
        ReadFloatArray
            Readable array containing the frequencies corresponding to the
            tune measurements.
        """
        ...
