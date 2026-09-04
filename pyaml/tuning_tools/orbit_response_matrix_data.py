"""Data model for measured orbit response matrices.

The data model stores the response matrix together with actuator and BPM names,
plane information, and optional RF response data.
"""

from dataclasses import dataclass
from typing import Optional

from ..validation import DynamicValidation, register_schema
from .response_matrix_data import ResponseMatrixData

PYAMLCLASS = "OrbitResponseMatrixData"


@register_schema
@dataclass
class OrbitResponseMatrixData(ResponseMatrixData, DynamicValidation):
    """Store orbit response matrix data and related metadata.

    In addition to the response matrix, variable names, and observable names
    provided by :class:`ResponseMatrixData`, this class stores the RF response
    and the plane associated with each variable and observable.

    Parameters
    ----------
    matrix : list[list[float]]
        Orbit response matrix. Each row corresponds to an observable and each
        column corresponds to a variable.
    variable_names : list[str] or None
        Names of the response-matrix variables, typically orbit correctors.
    observable_names : list[str]
        Names of the response-matrix observables, typically beam position
        monitors.
    rf_response : list[float] or None, optional
        Orbit response to an RF-frequency change.
    variable_planes : list[str] or None, optional
        Plane associated with each response-matrix variable, typically the
        plane of the corresponding actuator.
    observable_planes : list[str] or None, optional
        Plane associated with each response-matrix observable, typically the
        plane of the corresponding measurement.
    """

    rf_response: Optional[list[float]] = None
    variable_planes: Optional[list[str]] = None
    observable_planes: Optional[list[str]] = None
