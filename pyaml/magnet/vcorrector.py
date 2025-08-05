from .magnet import Magnet,MagnetConfigModel
from ..lattice.polynom_info import PolynomInfo

# Define the main class name for this module
PYAMLCLASS = "VCorrector"

class ConfigModel(MagnetConfigModel):...

class VCorrector(Magnet):    
    """Vertical Corrector class"""
    polynom = PolynomInfo('PolynomA',0)

    def __init__(self, cfg: ConfigModel):
        super().__init__(
            cfg.name,
            cfg.linked_elements if hasattr(cfg, "linked_elements") else None,
            cfg.hardware if hasattr(cfg, "hardware") else None,
            cfg.model if hasattr(cfg, "model") else None,
        )
        self._cfg = cfg



