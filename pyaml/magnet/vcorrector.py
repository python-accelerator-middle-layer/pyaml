from ..common import abstract
from ..lattice.polynom_info import PolynomInfo
from .corrector import RWCorrectorAngle
from .magnet import Magnet, MagnetConfigModel

# Define the main class name for this module
PYAMLCLASS = "VCorrector"


class ConfigModel(MagnetConfigModel): ...


class VCorrector(Magnet):
    """Vertical Corrector class"""

    polynom = PolynomInfo("PolynomA", 0)

    def __init__(self, cfg: ConfigModel):
        super().__init__(
            cfg.name,
            cfg.model if hasattr(cfg, "model") else None,
        )
        self._cfg = cfg
        self.__angle = RWCorrectorAngle(self)

    @property
    def angle(self) -> abstract.ReadWriteFloatScalar:
        """
        Set the kick angle.
        """
        return self.__angle
