
from datetime import datetime
from typing import Union

from enum import Enum, auto

import numpy as np

class Quality(Enum):
    VALID = auto()
    INVALID = auto()
    ALARM = auto()
    CHANGING = auto()
    WARNING = auto()
    def __str__(self):
        return self.name

class Value:
    """
    Represents a numerical value with associated quality and timestamp.

    This class wraps a scalar or NumPy array and can be used in arithmetic
    operations and comparisons. It also retains metadata like quality and timestamp.

    Parameters
    ----------
    value : float, int or numpy.ndarray
        The numerical value(s) to wrap.
    quality : Quality, optional
        The quality of the value. Defaults to Quality.VALID.
    timestamp : datetime, optional
        Timestamp associated with the value. Defaults to current time.
    """

    def __init__(self, value: Union[float, int, np.ndarray], quality: Quality = Quality.VALID, timestamp: datetime = None):
        self.value = value
        self.quality = quality
        self.timestamp = timestamp or datetime.now()

    def __repr__(self):
        """
        Return a string representation of the Value object.

        Returns
        -------
        str
            Human-readable representation.
        """
        return f"Value({self.value}, quality='{self.quality}', timestamp='{self.timestamp}')"

    def __float__(self):
        """
        Convert to float.

        Returns
        -------
        float
            The value converted to float.
        """
        return float(self.value)

    def __int__(self):
        """
        Convert to int.

        Returns
        -------
        int
            The value converted to int.
        """
        return int(self.value)

    def __eq__(self, other):
        """
        Compare for equality.

        Parameters
        ----------
        other : Value, scalar or numpy.ndarray
            The object to compare against.

        Returns
        -------
        bool
            True if values are equal, False otherwise.
        """
        if isinstance(other, Value):
            return np.array_equal(self.value, other.value)
        if isinstance(self.value, np.ndarray):
            return np.array_equal(self.value, other)
        return self.value == other

    def __lt__(self, other):
        """
        Less than comparison.

        Parameters
        ----------
        other : Value or scalar

        Returns
        -------
        bool
        """
        other_val = other.value if isinstance(other, Value) else other
        return self.value < other_val

    def __le__(self, other):
        """
        Less than or equal comparison.

        Parameters
        ----------
        other : Value or scalar

        Returns
        -------
        bool
        """
        other_val = other.value if isinstance(other, Value) else other
        return self.value <= other_val

    def __gt__(self, other):
        """
        Greater than comparison.

        Parameters
        ----------
        other : Value or scalar

        Returns
        -------
        bool
        """
        other_val = other.value if isinstance(other, Value) else other
        return self.value > other_val

    def __ge__(self, other):
        """
        Greater than or equal comparison.

        Parameters
        ----------
        other : Value or scalar

        Returns
        -------
        bool
        """
        other_val = other.value if isinstance(other, Value) else other
        return self.value >= other_val

    def __add__(self, other):
        """
        Add another value.

        Parameters
        ----------
        other : Value or scalar or numpy.ndarray
            Value to add.

        Returns
        -------
        Result of addition.
        """
        other_val = other.value if isinstance(other, Value) else other
        return self.value + other_val

    def __radd__(self, other):
        """
        Add from the right-hand side.

        Parameters
        ----------
        other : scalar or numpy.ndarray
            Value to add.

        Returns
        -------
        Result of addition.
        """
        return other + self.value

    def __sub__(self, other):
        """
        Subtract another value.

        Parameters
        ----------
        other : Value or scalar or numpy.ndarray
            Value to subtract.

        Returns
        -------
        Result of subtraction.
        """
        other_val = other.value if isinstance(other, Value) else other
        return self.value - other_val

    def __rsub__(self, other):
        """
        Subtract from the right-hand side.

        Parameters
        ----------
        other : scalar or numpy.ndarray
            Value to subtract.

        Returns
        -------
        Result of subtraction.
        """
        return other - self.value

    def __mul__(self, other):
        """
        Multiply by another value.

        Parameters
        ----------
        other : Value or scalar or numpy.ndarray
            Value to multiply with.

        Returns
        -------
        Result of multiplication.
        """
        other_val = other.value if isinstance(other, Value) else other
        return self.value * other_val

    def __rmul__(self, other):
        """
        Multiply from the right-hand side.

        Parameters
        ----------
        other : scalar or numpy.ndarray
            Value to multiply with.

        Returns
        -------
        Result of multiplication.
        """
        return other * self.value

    def __truediv__(self, other):
        """
        Divide by another value.

        Parameters
        ----------
        other : Value or scalar or numpy.ndarray
            Divisor.

        Returns
        -------
        Result of division.
        """
        other_val = other.value if isinstance(other, Value) else other
        return self.value / other_val

    def __rtruediv__(self, other):
        """
        Divide from the right-hand side.

        Parameters
        ----------
        other : scalar or numpy.ndarray
            Dividend.

        Returns
        -------
        Result of division.
        """
        return other / self.value

    def __neg__(self):
        """
        Negate the value.

        Returns
        -------
        Result of negation.
        """
        return -self.value

    def is_good(self) -> bool:
        """
        Check if the value quality is good.

        Returns
        -------
        bool
            True if the quality is VALID or CHANGING.
        """
        return self.quality in (Quality.VALID, Quality.CHANGING)
