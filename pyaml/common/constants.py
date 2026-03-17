"""
PyAML global constants

.. data:: HORIZONTAL_KICK_SIGN

    Horizontal kick sign convention for both kick an kick angle (default: -1).

"""

from enum import Enum

HORIZONTAL_KICK_SIGN: float = -1.0


class Action(Enum):
    """
    Action identifier for callback in measurement tools
    """

    APPLY = 0
    "Triggered imediatly after actuator exitation"
    RESTORE = 1
    "Triggered imediatly after actuator has been restored to initial value"
    MEASURE = 2
    "Triggered imediatly after measurement"
