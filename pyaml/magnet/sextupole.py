from ..control.element import ElementModel

from ..control.deviceaccess import DeviceAccess
from .magnet import Magnet
from .unitconv import UnitConv
from ..lattice.polynom_info import PolynomInfo

# Define the main class name for this module
PYAMLCLASS = "Sextupole"

class ConfigModel(ElementModel):

    hardware: DeviceAccess | None = None
    """Direct access to a magnet device that provides strength/current conversion"""
    unitconv: UnitConv | None = None
    """Object in charge of converting magnet strenghts to current"""

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



