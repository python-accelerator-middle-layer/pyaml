from typing import Optional

from pydantic import BaseModel, ConfigDict

PYAMLCLASS = "ResponseMatrix"


class ConfigModel(BaseModel):
    """
    Configuration model for response matrix

    Parameters
    ----------
    matrix : list[list[float]]
        Response matrix data
    input_names : list[str], optional
        Input names
    output_names : list[str]
        Output names
    rf_response : list[float], optional
        RF response data
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    matrix: list[list[float]]
    input_names: Optional[list[str]]
    output_names: list[str]
    rf_response: Optional[list[float]] = None
    inputs_plane: Optional[list[str]] = None
    outputs_plane: Optional[list[str]] = None


class ResponseMatrix(object):
    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
