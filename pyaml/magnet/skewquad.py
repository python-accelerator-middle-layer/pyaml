from .magnet import Magnet,MagnetConfigModel
from ..lattice.polynom_info import PolynomInfo

# Define the main class name for this module
PYAMLCLASS = "SkewQuad"

class ConfigModel(MagnetConfigModel):...

class SkewQuad(Magnet):    
    """SkewQuad class"""
    polynom = PolynomInfo('PolynomA',1)

    def __init__(self, cfg: ConfigModel):
        super().__init__(
            cfg.name,
            cfg.hardware if hasattr(cfg, "hardware") else None,
            cfg.model if hasattr(cfg, "model") else None,
        )
        self._cfg = cfg



