from typing import Optional

from .response_matrix_data import ConfigModel as ReponseMatrixDataConfigModel
from .response_matrix_data import ResponseMatrixData

PYAMLCLASS = "OrbitResponseMatrixData"


class ConfigModel(ReponseMatrixDataConfigModel):
    """
    Configuration model for orbit response matrix

    Parameters
    ----------
    rf_response : list[float], optional
        RF response data
    variable_names : list[str], optional
        Vaiable plane names, basically the plane of the actuators
    observable_names : list[str], optional
        Observable plane names, basically the plane of measurements
    """

    rf_response: Optional[list[float]] = None
    variable_planes: Optional[list[str]] = None
    observable_planes: Optional[list[str]] = None


class OrbitResponseMatrixData(ResponseMatrixData):
    """
    Orbit response matrix loader
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
