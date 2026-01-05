import numpy as np

from ..bpm.bpm import BPM
from ..common.abstract import ReadFloatArray
from ..control.deviceaccesslist import DeviceAccessList
from .element_array import ElementArray


class RWBPMPosition(ReadFloatArray):
    def __init__(self, name: str, bpms: list[BPM]):
        self.__bpms = bpms
        self.__name = name
        self.__aggregator: DeviceAccessList = None

    # Gets the values
    def get(self) -> np.array:
        if not self.__aggregator:
            return np.array([b.positions.get() for b in self.__bpms])
        else:
            return self.__aggregator.get().reshape(len(self.__bpms), 2)

    # Gets the unit of the values
    def unit(self) -> list[str]:
        return [b.positions.unit() for b in self.__bpms]

    # Set the aggregator (Control system only)
    def set_aggregator(self, agg: DeviceAccessList):
        self.__aggregator = agg


class RWBPMSinglePosition(ReadFloatArray):
    def __init__(self, name: str, bpms: list[BPM], idx: int):
        self.__bpms = bpms
        self.__name = name
        self.__idx = idx
        self.__aggregator: DeviceAccessList = None

    # Gets the values
    def get(self) -> np.array:
        if not self.__aggregator:
            return np.array([b.positions.get()[self.__idx] for b in self.__bpms])
        else:
            return self.__aggregator.get()

    # Gets the unit of the values
    def unit(self) -> list[str]:
        return [b.positions.unit() for b in self.__bpms]

    # Set the aggregator (Control system only)
    def set_aggregator(self, agg: DeviceAccessList):
        self.__aggregator = agg


class BPMArray(ElementArray):
    """
    Class that implements access to a BPM array

    Parameters
    ----------
    arrayName : str
        Array name
    bpms: list[BPM]
        BPM list, all elements must be attached to the same instance of
        either a Simulator or a ControlSystem.
    use_aggregator : bool
        Use aggregator to increase performance by using paralell
        access to underlying devices.

    Example
    -------

    An array can be retrieved from the configuration as in the following example::

        sr = Accelerator.load("acc.yaml")
        bpms = sr.design.get_bpms("BPMs")


    """

    def __init__(self, arrayName: str, bpms: list[BPM], use_aggregator=True):
        super().__init__(arrayName, bpms, use_aggregator)

        self.__hvpos = RWBPMPosition(arrayName, bpms)
        self.__hpos = RWBPMSinglePosition(arrayName, bpms, 0)
        self.__vpos = RWBPMSinglePosition(arrayName, bpms, 1)

        if use_aggregator and len(bpms) > 0:
            aggs = self.get_peer().create_bpm_aggregators(bpms)
            self.__hvpos.set_aggregator(aggs[0])
            self.__hpos.set_aggregator(aggs[1])
            self.__vpos.set_aggregator(aggs[2])

    @property
    def positions(self) -> RWBPMPosition:
        """
        Returns position of each bpm of this array
        """
        return self.__hvpos

    @property
    def h(self) -> RWBPMSinglePosition:
        """
        Returns horizontal position of each bpm of this array
        """
        return self.__hpos

    @property
    def v(self) -> RWBPMSinglePosition:
        """
        Returns vertical position of each bpm of this array
        """
        return self.__vpos
