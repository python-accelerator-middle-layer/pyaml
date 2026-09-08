from dataclasses import dataclass
from pathlib import Path

from pyaml.configuration.factory import Factory
from pyaml.validation import SchemaValidator

from .. import PyAMLException
from ..configuration.fileloader import load
from ..validation import DynamicValidation, register_schema

PYAMLCLASS = "ResponseMatrixData"


@register_schema
@dataclass
class ResponseMatrixData(DynamicValidation):
    """Response matrix data and its associated variable and observable names.

    Parameters
    ----------
    matrix : list[list[float]]
        Response matrix values. Each row corresponds to an observable and each
        column corresponds to a variable.
    variable_names : list[str] or None
        Names of the variables represented by the matrix columns, typically
        actuators. May be ``None`` if the names are unavailable.
    observable_names : list[str]
        Names of the observables represented by the matrix rows, typically
        measured quantities.
    """

    matrix: list[list[float]]
    observable_names: list[str]
    variable_names: list[str] | None = None

    @staticmethod
    def load(filename: str) -> "ResponseMatrixData":
        """Load response matrix data from a configuration file.

        Parameters
        ----------
        filename : str
            Path to the response matrix configuration file.

        Returns
        -------
        ResponseMatrixData
            Response matrix data constructed from the configuration file.

        Raises
        ------
        PyAMLException
            If the specified file does not exist.
        """
        path = Path(filename)
        if path.exists():
            config_dict = load(str(path.resolve()))
            SchemaValidator.validate(config_dict)
            return Factory.build(config_dict, ignore_external=False)
        else:
            raise PyAMLException(f"{filename}: file not found")
