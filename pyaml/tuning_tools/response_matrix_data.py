from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict

from pyaml.common.element import __pyaml_repr__
from pyaml.configuration.factory import Factory

from .. import PyAMLException
from ..configuration import ConfigurationSchema, register_schema
from ..configuration.fileloader import load


class ResponseMatrixDataSchema(ConfigurationSchema):
    """
    Base configuration model for response matrix

    Parameters
    ----------
    matrix : list[list[float]]
        Response matrix data (rows for observable, cols for variables)
    variable_names : list[str], optional
        Variable names, basically the actuators
    observables_names : list[str]
        Observable names, basically the measurements
    """

    matrix: list[list[float]]
    variable_names: Optional[list[str]]
    observable_names: list[str]


@register_schema(ResponseMatrixDataSchema)
class ResponseMatrixData(object):
    """
    Generic response matrix loader
    """

    def __init__(
        self,
        matrix: list[list[float]],
        variable_names: Optional[list[str]],
        observable_names: list[str],
    ):
        self._matrix = matrix
        self._variable_names = variable_names
        self._observable_names = observable_names

    @staticmethod
    def load(filename: str) -> "ResponseMatrixData":
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
