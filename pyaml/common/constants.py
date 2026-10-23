"""
Shared constants and callback action identifiers.

.. data:: HORIZONTAL_KICK_SIGN

   Sign convention applied to horizontal kicks and kick angles. A value of
   ``-1.0`` follows the convention used by the PyAML orbit and response-matrix
   tools.
"""

from enum import Enum

HORIZONTAL_KICK_SIGN: float = -1.0


class Action(Enum):
    """
    Identify callback points in measurement-tool workflows.

    Attributes
    ----------
    APPLY : int
        Callback triggered after an actuator excitation completes (including the waiting time).
    RESTORE : int
        Callback triggered immediately after restoring the actuator.
    MEASURE : int
        Callback triggered immediately after taking a measurement.
    INIT : int
        Triggered once before the measurement starts
    """

    APPLY = 0
    "Triggered after an actuator excitation completes (including the waiting time)."
    RESTORE = 1
    "Triggered immediately after restoring the actuator to its initial value."
    MEASURE = 2
    "Triggered immediately after taking a measurement."
    INIT = 3
    "Triggered once before the measurement starts"
    BEFORE_BPM_READING = 4
    "Triggered immediately before taking a measurement."
