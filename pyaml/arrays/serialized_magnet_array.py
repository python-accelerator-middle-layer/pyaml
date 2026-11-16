"""
Serialized Magnet Array module.

This module provides the deprecated serialized magnet array.
"""

import warnings

from ..magnet.serialized_magnet import SerializedMagnets
from .magnet_array import MagnetArray


class SerializedMagnetsArray(MagnetArray):
    """
    Array of serialized magnet groups.

    .. deprecated::
        A serialized family is a magnet: use :py:class:`.MagnetArray`, which reads and writes the average strength
        and the power-supply current of each family.

    Parameters
    ----------
    arrayName : str
        Array name
    magnets : list[SerializedMagnets]
        Serialized families, all attached to the same instance of either a Simulator or a ControlSystem.
    use_aggregator : bool
        Use aggregator to increase performance by using parallel access to underlying devices.
    """

    def __init__(self, arrayName: str, magnets: list[SerializedMagnets], use_aggregator=True):
        """
        Initialize the SerializedMagnetsArray.
        """
        warnings.warn(
            "SerializedMagnetsArray is deprecated, a serialized family is a magnet: use MagnetArray",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(arrayName, magnets, use_aggregator)
