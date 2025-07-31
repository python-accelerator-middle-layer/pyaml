from .magnet import Magnet,MagnetConfigModel
from ..lattice.polynom_info import PolynomInfo

# Define the main class name for this module
PYAMLCLASS = "SkewOctu"

class ConfigModel(MagnetConfigModel):...

class SkewOctu(Magnet):    
    """SkewOctu class"""
    polynom = PolynomInfo('PolynomA',3)

    def __init__(self, cfg: ConfigModel):
        super().__init__(
            cfg.name,
            cfg.hardware if hasattr(cfg, "hardware") else None,
            cfg.model if hasattr(cfg, "model") else None,
        )
        self._cfg = cfg



