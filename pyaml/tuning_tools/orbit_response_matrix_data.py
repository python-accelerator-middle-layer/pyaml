from typing import Optional

from .response_matrix_data import ConfigModel as ReponseMatrixDataSchema
from .response_matrix_data import ResponseMatrixData


class OrbitResponseMatrixDataSchema(ReponseMatrixDataSchema):
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

    def __init__(
        self,
        matrix: list[list[float]],
        variable_names: Optional[list[str]],
        observable_names: list[str],
        rf_response: Optional[list[float]] = None,
        variable_planes: Optional[list[str]] = None,
        observable_planes: Optional[list[str]] = None,
    ):
        super.__init__(matrix, variable_names, observable_names)
        self._rf_response = rf_response
        self._variable_planes = variable_planes
        self._observable_planes = observable_planes
