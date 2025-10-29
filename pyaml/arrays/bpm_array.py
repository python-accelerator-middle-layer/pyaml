from ..control.abstract import ReadFloatArray
from ..bpm.bpm import BPM
import numpy as np
from ..control.deviceaccesslist import DeviceAccessList

class RWBPMPosition(ReadFloatArray):

    def __init__(self, name:str, bpms:list[BPM]):
        self.__bpms = bpms
        self.__name = name
        self.aggregator:DeviceAccessList = None

    # Gets the values
    def get(self) -> np.array:
        if not self.aggregator:
            return np.array([b.positions.get() for b in self.__bpms])
        else:
            return self.aggregator.get()

    # Gets the unit of the values
    def unit(self) -> list[str]:
        return [b.positions.unit() for b in self.__bpms]

    # Set the aggregator (Control system only)
    def set_aggregator(self,agg:DeviceAccessList):
        self.aggregator = agg


class RWBPMSinglePosition(ReadFloatArray):

    def __init__(self, name:str, bpms:list[BPM],idx: int):
        self.__bpms = bpms
        self.__name = name
        self.__idx = idx
        self.aggregator:DeviceAccessList = None

    # Gets the values
    def get(self) -> np.array:
        if not self.aggregator:
            return np.array([b.positions.get()[self.__idx] for b in self.__bpms])
        else:
            return self.aggregator.get()

    # Gets the unit of the values
    def unit(self) -> list[str]:
        return [b.positions.unit()[self.__idx] for b in self.__bpms]

    # Set the aggregator (Control system only)
    def set_aggregator(self,agg:DeviceAccessList):
        self.aggregator = agg



class BPMArray(list[BPM]):
    """
    Class that implements access to a BPM array
    """

    def __init__(self,arrayName:str,bpms:list[BPM],agg:DeviceAccessList|None=None,aggh:DeviceAccessList|None=None,aggv:DeviceAccessList|None=None):
        """
        Construct a BPM array

        Parameters
        ----------
        arrayName : str
            Array name
        bpms: list[BPM]
            BPM iterator
        agg : DeviceAccessList
            Control system aggregator (Parralel access to list of device)
        """
        super().__init__(i for i in bpms)
        self.__name = arrayName
        self.__hvpos = RWBPMPosition(arrayName,bpms)
        self.__hpos = RWBPMSinglePosition(arrayName,bpms,0)
        self.__vpos = RWBPMSinglePosition(arrayName,bpms,1)

        if agg is not None:
            # Fill magnet aggregator
            for b in bpms:
                devs = b.model.get_pos_devices()
                agg.add_devices(devs)
                aggh.add_devices(devs[0])
                aggv.add_devices(devs[1])
            
        self.__hvpos.set_aggregator(agg)
        self.__hpos.set_aggregator(aggh)
        self.__vpos.set_aggregator(aggv)

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
        Give access to bpm H posttions of each bpm of this array
        """
        return self.__vpos

    


    