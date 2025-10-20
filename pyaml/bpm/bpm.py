from pyaml.lattice.element import Element, ElementConfigModel
from pyaml.lattice.abstract_impl import RBpmPositionArray, RWBpmOffsetArray, RWBpmTiltScalar
from ..control.deviceaccess import DeviceAccess
from ..control import abstract
from typing import Self
from pyaml.bpm.bpm_model import BPMModel

PYAMLCLASS = "BPM"

class ConfigModel(ElementConfigModel):
    """
    Class providing access to BPM configuration parameters
    """

    def __init__(self):
        """
        Construct a BPM configuration model

        Parameters
        ----------
        """
        hardware: DeviceAccess | None = None
        """Direct access to a magnet device that provides strength/current conversion"""
        model: BPMModel | None = None
        """Object in charge of converting magnet strenghts to power supply values"""



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

        self.__hardware = cfg.hardware if hasattr(cfg, "hardware") else None
        self.__model = cfg.model if hasattr(cfg, "model") else None
        self.__cfg = cfg
    @property
    def hardware(self) -> abstract.ReadWriteFloatScalar:
        if self.__hardware is None:
            raise Exception(f"{str(self)} has no model that supports hardware units")
        return self.__hardware

    @property
    def model(self) -> BPMModel:
         return self.__model

    def attach(self, positions: RBpmPositionArray , offset: RWBpmOffsetArray,
               tilt: RWBpmTiltScalar) -> Self:
        # Attach positions, offset and tilt attributes and returns a new
        # reference
        obj = self.__class__(self._cfg)
        obj.__model = self.__model
        obj.__hardware = self.__hardware
        # obj.__positions = positions
        # obj.__offset = offset
        # obj.__tilt = tilt
        return obj
        
