from pathlib import Path

from pydantic import SerializeAsAny

from .Magnet import Magnet
from . import Quadrupole
from . import UnitConv
from ..control import Abstract
from ..lattice.RWStrengthArray import RWStrengthArray
from ..configuration.models import ConfigBase, recursively_construct_element_from_cfg


class Config(ConfigBase):
    """CombinedFunctionMagnet class"""

    name: str
    H: str | None = None
    V: str | None = None
    Q: str | None = None
    SQ: str | None = None
    S: str | None = None
    O: str | None = None
    unitconv: str | Path | SerializeAsAny[UnitConv.Config] | None = None

    @classmethod
    def validate_unitconv(cls, v, values):
        return cls.validate_sub_config(v, values, "unitconv", UnitConv.Config)


class CombinedFunctionMagnet(Magnet):
    """CombinedFunctionMagnet class"""

    def __init__(self, cfg: Config):
        self._cfg = cfg

        # def __init__(self, name:str, H:str=None,V:str=None,Q:str=None,SQ:str=None,S:str=None,O:str=None, unitconv: UnitConv = None):
        super().__init__(cfg.name)

        if cfg.unitconv is None:
            self.unitconv = None
        else:
            self.unitconv = recursively_construct_element_from_cfg(cfg.unitconv)

        # TODO Count number of defined strength
        # TODO Check that UnitConv is coherent (number of strengths same as number of defined single function magnet)
        self.multipole: Abstract.ReadWriteFloatArray = RWStrengthArray(
            cfg.name, self.unitconv, 3
        )

        idx = 0
        # Create single function magnet
        if cfg.H is not None:
            # self.horz = HorizontalCorrector(H)  # TODO implement HorizontalCorrector
            # self.horz.setSource(self.multipole,idx)
            idx += 1

        if cfg.V is not None:
            # self.vert = VerticalCorrector(V) # TODO implement VerticalCorrector
            # self.setSource(self.multipole,idx)
            idx += 1

        if cfg.Q is not None:
            q_cfg = Quadrupole.Config(name=cfg.Q)
            self.quad = Quadrupole.Quadrupole(q_cfg)
            self.quad.setSource(self.multipole, idx)
            idx += 1

    def __repr__(self):
        return "%s(name=%s, unitconv=%s)" % (
            self.__class__.__name__,
            self.name,
            self.unitconv,
        )
