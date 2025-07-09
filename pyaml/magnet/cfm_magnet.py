from pydantic import SerializeAsAny
from pydantic import BaseModel
from scipy.constants import speed_of_light

from .unitconv import UnitConv
from .magnet import Magnet
from ..control import abstract
from ..control.element import ElementModel
from ..lattice.abstract_impl import RWStrengthArray
from ..control.element import Element

from .hcorrector import HCorrector
from .vcorrector import VCorrector
from .quadrupole import Quadrupole
from .skewquad import SkewQuad
from .sextupole import Sextupole
from .skewsext import SkewSext
from .octupole import Octupole
from .skewoctu import SkewOctu
from .decapole import Decapole
from .skewdeca import SkewDeca

_fmap:dict = {
    "B0":HCorrector,
    "A0":VCorrector,
    "B1":Quadrupole,
    "A1":SkewQuad,
    "B2":Sextupole,
    "A2":SkewSext,
    "B3":Octupole,
    "A3":SkewOctu,
    "B4":Decapole,
    "A4":SkewDeca
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

        self.multipole: abstract.ReadWriteFloatArray = RWStrengthArray(
            cfg.name, self.unitconv
        )

        idx = 0
        for m in cfg.mapping:

            # Check mapping validity
            if len(m)!=2:
                raise Exception("Invalid CombinedFunctionMagnet mapping for {m}")
            if not m[0] in _fmap:
                raise Exception(m[0] + " not implemented for combined function magnet")
            if m[0] not in self.unitconv._cfg.multipoles:
                raise Exception(m[0] + " not found in underlying unitconv")

            # Construct a virtual single function magnet for each function
            args = {"name":m[1]}
            mclass:Magnet = _fmap[m[0]](ElementModel(**args))
            mclass.set_source(self.multipole,idx)
            setattr(self,m[0],mclass)
            idx += 1

    def set_energy(self,E:float):
        if(self.unitconv is not None):
            self.unitconv.set_magnet_rigidity(E/speed_of_light)
