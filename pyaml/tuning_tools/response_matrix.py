from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict

from pyaml.common.element import __pyaml_repr__
from pyaml.configuration.factory import Factory

from .. import PyAMLException
from ..configuration.fileloader import load

PYAMLCLASS = "ResponseMatrix"


class ConfigModel(BaseModel):
    """
    Configuration model for response matrix

    Parameters
    ----------
    matrix : list[list[float]]
        Response matrix data
    input_names : list[str], optional
        Input names, basically the actuators
    output_names : list[str]
        Output names, basically the measurements
    rf_response : list[float], optional
        RF response data
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    matrix: list[list[float]]
    input_names: Optional[list[str]]
    output_names: list[str]
    rf_response: Optional[list[float]] = None
    input_planes: Optional[list[str]] = None
    output_planes: Optional[list[str]] = None


class ResponseMatrix(object):
    """
    Generic response matrix loader
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg

    @staticmethod
    def load(filename: str) -> None:
        """
        Load a reponse matrix from a configuration file
        """
        path = Path(filename)
        if path.exists():
            config_dict = load(str(path.resolve()))
            return Factory.depth_first_build(config_dict, ignore_external=False)
        else:
            raise PyAMLException(f"{filename}: file not found")

    def __repr__(self):
        return __pyaml_repr__(self)
