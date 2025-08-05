from .magnet import Magnet,MagnetConfigModel
from ..lattice.polynom_info import PolynomInfo

# Define the main class name for this module
PYAMLCLASS = "SkewSext"

class ConfigModel(MagnetConfigModel):...

class SkewSext(Magnet):    
    """SkewSext class"""
    polynom = PolynomInfo('PolynomA',2)

    def __init__(self, cfg: ConfigModel):
        super().__init__(
            cfg.name,
            cfg.linked_elements if hasattr(cfg, "linked_elements") else None,
            cfg.hardware if hasattr(cfg, "hardware") else None,
            cfg.model if hasattr(cfg, "model") else None,
        )
        self._cfg = cfg



