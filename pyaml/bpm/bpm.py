from pyaml.lattice.element import Element, ElementConfigModel
from pyaml.pyaml.lattice.abstract_impl import RBpmPositionArray, RWBpmOffsetArray, RBpmTiltScalar
from ..control.deviceaccess import DeviceAccess
from ..control import abstract
from typing import Self

PYAMLCLASS = "BPM"

class BPMConfigModel(ElementConfigModel):
    """
    Class providing access to BPM configuration parameters
    """

    def __init__(self, hardware_name: str):
        """
        Construct a BPM configuration model

        Parameters
        ----------
        name : str
            Element name
        """
        hardware_name: str 

class BPM (Element):
    """
    Class providing access to one BPM of a physical or simulated lattice
    """

    def __init__(self, name: str, hardware: DeviceAccess = None, model:
                 BPMModel = None):
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
        super().__init__(name)
        self.__model = model
        self.__hardware = hardware
        self.__positions = None
        self.__offset = None
        self.__tilt = None

        if hardware is not None:
            # TODO
            # Direct access to a BPM device that supports beam position
            # computation
            raise Exception(
                "%s, hardware access not implemented" %
                (self.__class__.__name__, name))
    @property
    def hardware(self) -> abstract.ReadWriteFloatScalar:
        if self.__hardware is None:
            raise Exception(f"{str(self)} has no model that supports hardware units")
        return self.__hardware

    def attach(self, positions: RBpmPositionArray , offset: RWBpmOffsetArray, tilt: RBpmTiltScalar) -> Self:
        # Attach positions, offset and tilt attributes and returns a new
        # reference
        obj = self.__class__(self._cfg)
        obj.__model = self.__model
        obj.__hardware = self.__hardware
        obj.__positions = positions
        obj.__offset = offset
        obj.__tilt = tilt
        return obj
        
