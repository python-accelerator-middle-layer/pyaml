from pydantic import SerializeAsAny
from pydantic import BaseModel

from .magnet import Magnet
from . import quadrupole 
from .unitconv import UnitConv
from ..control import abstract
from ..lattice.abstract_impl import RWStrengthArray

# Define the main class name for this module
PYAMLCLASS = "CombinedFunctionMagnet"

class ConfigModel(BaseModel):

    name: str
    A0: str | None = None
    B0: str | None = None
    A1: str | None = None
    B1: str | None = None
    A2: str | None = None
    B2: str | None = None
    A3: str | None = None
    B3: str | None = None
    A4: str | None = None
    B4: str | None = None
    A5: str | None = None
    B5: str | None = None
    unitconv: UnitConv | None = None

class CombinedFunctionMagnet(Magnet):
    """CombinedFunctionMagnet class"""

    def __init__(self, cfg: ConfigModel):

        super().__init__(cfg.name)

        self.unitconv = cfg.unitconv

        # TODO Count number of defined strength
        # TODO Check that UnitConv is coherent (number of strengths same as number of defined single function magnet)
        self.multipole: abstract.ReadWriteFloatArray = RWStrengthArray(
            cfg.name, self.unitconv, 3
        )

        idx = 0
        # Create single function magnet
        if cfg.B0 is not None:
            # self.b0 = HorizontalCorrector(H)  # TODO implement HorizontalCorrector
            # self.b0.setSource(self.multipole,idx)
            idx += 1

        if cfg.A0 is not None:
            # self.a0 = VerticalCorrector(V) # TODO implement VerticalCorrector
            # self.a0(self.multipole,idx)
            idx += 1

        if cfg.B1 is not None:
            q_cfg = quadrupole.ConfigModel(name=cfg.B1)
            self.b1 = quadrupole.Quadrupole(q_cfg)
            self.b1.setSource(self.multipole, idx)
            idx += 1

        if cfg.A1 is not None:
            #self.b0 = SkewQuadrupole(q_cfg)
            #self.b0.setSource(self.multipole, idx)
            idx += 1

    def __repr__(self):
        return "%s(name=%s, unitconv=%s)" % (
            self.__class__.__name__,
            self.name,
            self.unitconv,
        )
