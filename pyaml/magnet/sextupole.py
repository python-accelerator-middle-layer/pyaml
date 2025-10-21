from .magnet import Magnet,MagnetConfigModel
from ..lattice.polynom_info import PolynomInfo

# Define the main class name for this module
PYAMLCLASS = "Sextupole"

class ConfigModel(MagnetConfigModel):...

class Sextupole(Magnet):    
    """Sextupole class"""
    polynom = PolynomInfo('PolynomB',2)

    def __init__(self, cfg: ConfigModel):
        super().__init__(
            cfg.name,
            cfg.model if hasattr(cfg, "model") else None,
        )
        self._cfg = cfg



