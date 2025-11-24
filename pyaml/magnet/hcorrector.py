from ..lattice.polynom_info import PolynomInfo
from ..common import abstract
from .corrector import RWCorrectorAngle
from ..common.constants import HORIZONATL_KICK_SIGN

# Define the main class name for this module
PYAMLCLASS = "HCorrector"


class ConfigModel(MagnetConfigModel): ...


class HCorrector(Magnet):
    """Horizontal Corrector class"""
    polynom = PolynomInfo('PolynomB',0,HORIZONATL_KICK_SIGN)

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
        return self.ange



