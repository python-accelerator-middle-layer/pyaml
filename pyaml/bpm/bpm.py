from pyaml.lattice.element import Element, ElementConfigModel
from pyaml.lattice.abstract_impl import RBpmArray, RWBpmOffsetArray, RWBpmTiltScalar
from ..control.deviceaccess import DeviceAccess
from ..control import abstract
from typing import Self
from pyaml.bpm.bpm_model import BPMModel

PYAMLCLASS = "BPM"

class ConfigModel(ElementConfigModel):

        model: BPMModel | None = None
        """Object in charge of BPM modeling"""



class BPM(Element):
    """
    Class providing access to one BPM of a physical or simulated lattice
    """

    def __init__(self, cfg: ConfigModel):
        """
        Construct a BPM

        Parameters
        ----------
        name : str
            Element name
        hardware : DeviceAccess
            Direct access to a hardware (bypass the BPM model)
        model : BPMModel
            BPM model in charge of computing beam position
        """
        
        super().__init__(cfg.name)

        self.__model = cfg.model if hasattr(cfg, "model") else None
        self._cfg = cfg
        self.__positions = None
        self.__offset = None
        self.__tilt = None

    @property
    def model(self) -> BPMModel:
         return self.__model

    @property
    def positions(self) -> RBpmArray:
        if self.__positions is None:
            raise Exception(f"{str(self)} has no attached positions") 
        return self.__positions

    @property
    def offset(self) -> RWBpmOffsetArray:
        if self.__offset is None:
            raise Exception(f"{str(self)} has no attached offset")
        return self.__offset

    @property
    def tilt(self) -> RWBpmTiltScalar:
        if self.__tilt is None:
            raise Exception(f"{str(self)} has no attached tilt")
        return self.__tilt

    def attach(self, positions: RBpmArray , offset: RWBpmOffsetArray,
               tilt: RWBpmTiltScalar) -> Self:
        # Attach positions, offset and tilt attributes and returns a new
        # reference
        obj = self.__class__(self._cfg)
        obj.__model = self.__model
        obj.__positions = positions
        obj.__offset = offset
        obj.__tilt = tilt
        return obj
        
