from .magnet import Magnet,MagnetModel
from ..lattice.polynom_info import PolynomInfo

# Define the main class name for this module
PYAMLCLASS = "Sextupole"

class ConfigModel(MagnetModel):...

class Sextupole(Magnet):    
    """Sextupole class"""
    polynom = PolynomInfo('PolynomB',2)

    def __init__(self, cfg: ConfigModel):
        super().__init__(
            cfg.name,
            cfg.hardware if hasattr(cfg, "hardware") else None,
            cfg.unitconv if hasattr(cfg, "unitconv") else None,
        )
        self._cfg = cfg



