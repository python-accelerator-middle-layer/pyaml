from .magnet import Magnet,MagnetModel
from ..lattice.polynom_info import PolynomInfo

# Define the main class name for this module
PYAMLCLASS = "HCorrector"

class ConfigModel(MagnetModel):...

class HCorrector(Magnet):
    """Horizontal Corrector class"""
    polynom = PolynomInfo('PolynomB',0)

    def __init__(self, cfg: ConfigModel):
        super().__init__(
            cfg.name,
            cfg.hardware if hasattr(cfg, "hardware") else None,
            cfg.model if hasattr(cfg, "model") else None,
        )
        self._cfg = cfg

