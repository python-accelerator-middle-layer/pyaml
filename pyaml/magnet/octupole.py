from .magnet import Magnet,MagnetModel
from ..lattice.polynom_info import PolynomInfo

# Define the main class name for this module
PYAMLCLASS = "Octupole"

class ConfigModel(MagnetModel):...

class Octupole(Magnet):    
    """Octupole class"""
    polynom = PolynomInfo('PolynomB',3)

    def __init__(self, cfg: ConfigModel):
        super().__init__(
            cfg.name,
            cfg.hardware if hasattr(cfg, "hardware") else None,
            cfg.model if hasattr(cfg, "model") else None,
        )
        self._cfg = cfg
