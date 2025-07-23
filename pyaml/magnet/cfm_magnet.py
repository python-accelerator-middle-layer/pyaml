from pydantic import SerializeAsAny
from scipy.constants import speed_of_light

from .unitconv import UnitConv
from ..lattice.element import ElementModel
from ..lattice.element import Element
from ..control import abstract
from ..control.abstract import RWMapper

from .hcorrector import HCorrector
from .vcorrector import VCorrector
from .quadrupole import Quadrupole
from .skewquad import SkewQuad
from .sextupole import Sextupole
from .skewsext import SkewSext
from .octupole import Octupole
from .skewoctu import SkewOctu
from .magnet import Magnet

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

class ConfigModel(ElementModel):

    mapping: list[list[str]]
    """Name mapping for multipoles (i.e. [[B0,C01A-H],[A0,C01A-H],[B2,C01A-S]])"""
    unitconv: UnitConv | None = None
    """Object in charge of converting magnet strenghts to currents"""

class CombinedFunctionMagnet(Element):
    """CombinedFunctionMagnet class"""

    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg.name)
        self._cfg = cfg
        self.unitconv = cfg.unitconv

        if self.unitconv is not None and not hasattr(self.unitconv._cfg,"multipoles"):
            raise Exception(f"{cfg.name} unitconv: mutipoles field required for combined function magnet")

        idx = 0
        self.polynoms = []
        for m in cfg.mapping:
            # Check mapping validity
            if len(m)!=2:
                raise Exception("Invalid CombinedFunctionMagnet mapping for {m}")
            if not m[0] in _fmap:
                raise Exception(m[0] + " not implemented for combined function magnet")
            if m[0] not in self.unitconv._cfg.multipoles:
                raise Exception(m[0] + " not found in underlying unitconv")
            self.polynoms.append(_fmap[m[0]].polynom)

    def attach(self, strengths: abstract.ReadWriteFloatArray, currents: abstract.ReadWriteFloatArray) -> list[Magnet]:

            # Construct a single function magnet for each multipole of this combined function magnet        
            l = []
            for idx,m in enumerate(self._cfg.mapping):
                args = {"name":m[1]}
                mclass:Magnet = _fmap[m[0]](ElementModel(**args))
                strength = RWMapper(strengths,idx)
                currents = RWMapper(currents,idx)
                l.append(mclass.attach(strength,currents))
            return l
    
    def set_energy(self,E:float):
        if(self.unitconv is not None):
            self.unitconv.set_magnet_rigidity(E/speed_of_light)
