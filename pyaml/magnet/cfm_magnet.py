
from .model import MagnetModel
from ..common.element import Element,ElementConfigModel
from ..common import abstract
from ..common.abstract import RWMapper
from ..common.exception import PyAMLException
from .hcorrector import HCorrector
from .vcorrector import VCorrector
from .quadrupole import Quadrupole
from .skewquad import SkewQuad
from .sextupole import Sextupole
from .skewsext import SkewSext
from .octupole import Octupole
from .skewoctu import SkewOctu
from .magnet import Magnet,MagnetConfigModel
from ..configuration import Factory

from scipy.constants import speed_of_light

_fmap:dict = {
    "B0":HCorrector,
    "A0":VCorrector,
    "B1":Quadrupole,
    "A1":SkewQuad,
    "B2":Sextupole,
    "A2":SkewSext,
    "B3":Octupole,
    "A3":SkewOctu
}

# Define the main class name for this module
PYAMLCLASS = "CombinedFunctionMagnet"

class ConfigModel(ElementConfigModel):

    mapping: list[list[str]]
    """Name mapping for multipoles (i.e. [[B0,C01A-H],[A0,C01A-H],[B2,C01A-S]])"""
    model: MagnetModel | None = None
    """Object in charge of converting magnet strenghts to currents"""

class CombinedFunctionMagnet(Element):
    """CombinedFunctionMagnet class"""

    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg.name)
        self._cfg = cfg
        self.model = cfg.model
        self.virtuals:list[Magnet] = []

        if self.model is not None and not hasattr(self.model._cfg,"multipoles"):
            raise PyAMLException(f"{cfg.name} model: mutipoles field required for combined function magnet")

        idx = 0
        self.polynoms = []
        for idx,m in enumerate(cfg.mapping):
            # Check mapping validity
            if len(m)!=2:
                raise PyAMLException("Invalid CombinedFunctionMagnet mapping for {m}")
            if not m[0] in _fmap:
                raise PyAMLException(m[0] + " not implemented for combined function magnet")
            if m[0] not in self.model._cfg.multipoles:
                raise PyAMLException(m[0] + " not found in underlying magnet model")
            self.polynoms.append(_fmap[m[0]].polynom)
            # Create the virtual magnet for the correspoding multipole
            vm = self.create_virutal_manget(m[1],m[0])
            self.virtuals.append(vm)
            # Register the virtual element in the factory to have a coherent factory and improve error reporting
            Factory.register_element(vm)

    def create_virutal_manget(self,name:str,idx:int) -> Magnet:
            args = {"name":name,"model":self.model}
            mVirtual:Magnet = _fmap[idx](MagnetConfigModel(**args))
            mVirtual.set_model_name(self.get_name())
            return mVirtual

    def attach(self, peer, strengths: abstract.ReadWriteFloatArray, hardwares: abstract.ReadWriteFloatArray) -> list[Magnet]:
            # Construct a single function magnet for each multipole of this combined function magnet        
            l = []
            for idx,m in enumerate(self._cfg.mapping):
                strength = RWMapper(strengths,idx)
                hardware = RWMapper(hardwares,idx) if self.model.has_hardware() else None
                l.append(self.virtuals[idx].attach(peer,strength,hardware))
            return l
    
    def set_energy(self,E:float):
        if(self.model is not None):
            self.model.set_magnet_rigidity(E/speed_of_light)
