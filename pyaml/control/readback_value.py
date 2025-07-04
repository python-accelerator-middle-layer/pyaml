
from datetime import datetime
from typing import Union

from enum import Enum, auto

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
    Can be used like a float or int in mathematical operations.
    """

    def __init__(self, value: Union[float, int], quality: Quality = Quality.VALID, timestamp: datetime = None):
        self.value = value
        self.quality = quality
        self.timestamp = timestamp or datetime.now()

    def __repr__(self):
        return f"Value({self.value}, quality='{self.quality}', timestamp='{self.timestamp}')"

    def __float__(self):
        return float(self.value)

    def __int__(self):
        return int(self.value)

    def __eq__(self, other):
        return float(self) == float(other)

    def __lt__(self, other):
        return float(self) < float(other)

    def __le__(self, other):
        return float(self) <= float(other)

    def __gt__(self, other):
        return float(self) > float(other)

    def __ge__(self, other):
        return float(self) >= float(other)

    def __add__(self, other):
        return float(self) + float(other)

    def __radd__(self, other):
        return float(other) + float(self)

    def __sub__(self, other):
        return float(self) - float(other)

    def __rsub__(self, other):
        return float(other) - float(self)

    def __mul__(self, other):
        return float(self) * float(other)

    def __rmul__(self, other):
        return float(other) * float(self)

    def __truediv__(self, other):
        return float(self) / float(other)

    def __rtruediv__(self, other):
        return float(other) / float(self)

    def __neg__(self):
        return -float(self)

    def is_good(self):
        """Return True if the quality is considered good."""
        return self.quality in [Quality.VALID, Quality.CHANGING]
