from typing import Optional

from .response_matrix_data import ConfigModel as ReponseMatrixDataConfigModel
from .response_matrix_data import ResponseMatrixData

PYAMLCLASS = "OrbitResponseMatrixData"


class ConfigModel(ReponseMatrixDataConfigModel):
    """
    Base configuration model for response matrix

    Parameters
    ----------
    rf_response : list[float], optional
        RF response data
    input_names : list[str], optional
        Input plane names, basically the plane of the actuators
    output_names : list[str], optional
        Output plane names, basically the plane of measurements
    """

    rf_response: Optional[list[float]] = None
    input_planes: Optional[list[str]] = None
    output_planes: Optional[list[str]] = None


class OrbitResponseMatrixData(ResponseMatrixData):
    """
    Orbit response matrix loader
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
