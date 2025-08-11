from abc import ABCMeta, abstractmethod
import numpy as np

class Curve(metaclass=ABCMeta):
    """
    Abstract class providing access to a curve
    """

    @abstractmethod
    def get_curve(self) -> np.array:
        """
        Returns the curve (n rows,2 columns).
        Curve is expected to be monotonic (non-decreasing or non-increasing).        
        """
        pass

    @classmethod
    def inverse(cls, curve:np.array) -> np.array:
        """
        Returns the inverse curve.
        Basically swap x and y and sort y in ascending order.

        Parameters
        ----------
        curve : np.array
            Curve to be inverted
        """
        __curve = curve
        __sortedCurve = __curve[__curve[:,1].argsort()]
        return __sortedCurve[:,[1,0]]
