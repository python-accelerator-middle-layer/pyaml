from ..common.abstract import ReadFloatArray
from ..bpm.bpm import BPM
from ..control.deviceaccesslist import DeviceAccessList

import numpy as np

class RWBPMPosition(ReadFloatArray):

    def __init__(self, name:str, bpms:list[BPM]):
        self.__bpms = bpms
        self.__name = name
        self.__aggregator:DeviceAccessList = None

    # Gets the values
    def get(self) -> np.array:
        if not self.__aggregator:
            return np.array([b.positions.get() for b in self.__bpms])
        else:  
            return self.__aggregator.get().reshape(len(self.__bpms),2)

    # Gets the unit of the values
    def unit(self) -> list[str]:
        return [b.positions.unit() for b in self.__bpms]

    # Set the aggregator (Control system only)
    def set_aggregator(self,agg:DeviceAccessList):
        self.__aggregator = agg


class RWBPMSinglePosition(ReadFloatArray):

    def __init__(self, name:str, bpms:list[BPM],idx: int):
        self.__bpms = bpms
        self.__name = name
        self.__idx = idx
        self.__aggregator:DeviceAccessList = None

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
    def set_aggregator(self,agg:DeviceAccessList):
        self.__aggregator = agg



class BPMArray(list[BPM]):
    """
    Class that implements access to a BPM array
    """

    def __init__(self,arrayName:str,bpms:list[BPM],holder = None):
        """
        Construct a BPM array

        Parameters
        ----------
        arrayName : str
            Array name
        bpms: list[BPM]
            BPM iterator
        holder : Element holder
            Holder (Simulator or Control System) that contains element of this array used for aggregator
        """
        super().__init__(i for i in bpms)
        self.__name = arrayName
        self.__hvpos = RWBPMPosition(arrayName,bpms)
        self.__hpos = RWBPMSinglePosition(arrayName,bpms,0)
        self.__vpos = RWBPMSinglePosition(arrayName,bpms,1)

        if holder is not None:    
            aggs = holder.create_bpm_aggregators(bpms)
            self.__hvpos.set_aggregator(aggs[0])
            self.__hpos.set_aggregator(aggs[1])
            self.__vpos.set_aggregator(aggs[2])

    @property
    def positions(self) -> RWBPMPosition:
        """
        Give access to bpm posttions of each bpm of this array
        """
        return self.__hvpos

    @property
    def h(self) -> RWBPMSinglePosition:
        """
        Give access to bpm H posttions of each bpm of this array
        """
        return self.__hpos

    @property
    def v(self) -> RWBPMSinglePosition:
        """
        Give access to bpm V posttions of each bpm of this array
        """
        return self.__vpos

    


    