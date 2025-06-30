from pathlib import Path

from pydantic import field_validator, SerializeAsAny

from .Magnet import Magnet
from . import UnitConv
from ..control import Abstract, Device
from ..lattice.RWStrengthScalar import RWStrengthScalar
from ..lattice.RWMapper import RWMapper
from ..lattice.RCurrentScalar import RCurrentScalar
from ..configuration.models import ConfigBase, recursively_construct_element_from_cfg


class Config(ConfigBase):
    name: str
    hardware: Device.Config | None = None
    unitconv: str | Path | SerializeAsAny[UnitConv.Config] | None = None

    @field_validator("unitconv", mode="before")
    def validate_unitconv(cls, v, values):
        return cls.validate_sub_config(v, values, "unitconv", UnitConv.Config)


class Quadrupole(Magnet):
    """Quadrupole class"""

    def __init__(self, cfg: Config):
        self._cfg = cfg

        super().__init__(cfg.name)

        self.unitconv = None

        if cfg.hardware is not None:
            # TODO
            # Direct access to a magnet device that supports strength/current conversion
            raise Exception(
                "Quadrupole %s, hardware access not implemented" % (cfg.name)
            )
        else:
            # In case of unitconv is none, no control system access possible
            if cfg.unitconv is None:
                self.unitconv = None
            else:
                self.unitconv = recursively_construct_element_from_cfg(cfg.unitconv)

        self.strength: Abstract.ReadWriteFloatScalar = RWStrengthScalar(
            cfg.name, self.unitconv
        )
        self.current: Abstract.ReadFloatScalar = RCurrentScalar(self.unitconv)

    """Virtual single function magnet"""

    def setSource(self, source: Abstract.ReadWriteFloatArray, idx: int):
        # Override strength, map single strength to multipole
        self.strength: Abstract.ReadWriteFloatScalar = RWMapper(source, idx)

    def __repr__(self):
        return "%s(name=%s, unitconv=%s)" % (
            self.__class__.__name__,
            self.name,
            self.unitconv,
        )
