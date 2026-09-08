"""
Excitation-curve interfaces for magnet calibration.

An excitation curve represents paired magnet-strength and hardware values as
an ``(n, 2)`` array. Concrete implementations provide those points from a
file or in-memory data, while :class:`Curve` supplies the inverse-curve
operation used for reverse conversion.
"""

from abc import ABCMeta, abstractmethod

import numpy as np


class Curve(metaclass=ABCMeta):
    """
    Define the interface for a monotonic magnet excitation curve.

    Curves are represented by two columns of paired values and are used to
    interpolate between physical magnet strengths and hardware setpoints.
    """

    @abstractmethod
    def get_curve(self) -> np.array:
        """
        Returns the curve (n rows,2 columns).
        Curve is expected to be monotonic (non-decreasing or non-increasing).
        """
        pass

    @classmethod
    def inverse(cls, curve: np.array) -> np.array:
        """
        Returns the inverse curve.
        Basically swap x and y and sort y in ascending order.

        Parameters
        ----------
        curve : np.array
            Curve to be inverted
        """
        __curve = curve
        __sortedCurve = __curve[__curve[:, 1].argsort()]
        return __sortedCurve[:, [1, 0]]
