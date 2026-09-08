"""
Orbit measurement and correction tools.

The :class:`Orbit` tool reads orbit response data, computes corrector changes,
and applies horizontal, vertical, and optional RF corrections.
"""

import logging
from dataclasses import asdict
from pathlib import Path
from typing import Literal, Optional, Union

import numpy as np
from pySC import ResponseMatrix as pySC_ResponseMatrix
from pySC.apps import orbit_correction

from ..arrays.magnet_array import MagnetArray
from ..common.exception import PyAMLException
from ..external.pySC_interface import pySCInterface
from ..rf.rf_plant import RFPlant
from ..validation import DynamicValidation, register_schema
from .orbit_response_matrix_data import OrbitResponseMatrixData
from .tuning_tool import TuningTool

logger = logging.getLogger(__name__)
logging.getLogger("pyaml.external.pySC").setLevel(logging.WARNING)

PYAMLCLASS = "Orbit"


@register_schema
class Orbit(TuningTool, DynamicValidation):
    """
    Correct the measured orbit using a configured response matrix.

    Parameters
    ----------
    name : str
        Name of the orbit tool.
    bpm_array_name : str
        Name of the BPM array used for orbit readback.
    hcorr_array_name : str
        Name of the horizontal corrector array.
    vcorr_array_name : str
        Name of the vertical corrector array.
    response_matrix : Union[str, OrbitResponseMatrixData]
        Orbit response matrix or path to a serialized matrix.
    rf_plant_name : Optional[str]
        Optional RF plant used for RF orbit correction.
    singular_values : Optional[int]
        Common number of singular values retained for both planes.
    singular_values_H : Optional[int]
        Number of horizontal singular values retained.
    singular_values_V : Optional[int]
        Number of vertical singular values retained.
    virtual_target : float
        Target value for virtual orbit correction.
    """

    def __init__(
        self,
        name: str,
        bpm_array_name: str,
        hcorr_array_name: str,
        vcorr_array_name: str,
        response_matrix: Union[str, OrbitResponseMatrixData],
        rf_plant_name: Optional[str] = None,
        singular_values: Optional[int] = None,
        singular_values_H: Optional[int] = None,
        singular_values_V: Optional[int] = None,
        virtual_target: float = 0,
    ):
        """
        Initialize the Orbit.

        Parameters
        ----------
        name : str
            Name of the orbit tool.
        bpm_array_name : str
            Name of the BPM array used for orbit readback.
        hcorr_array_name : str
            Name of the horizontal corrector array.
        vcorr_array_name : str
            Name of the vertical corrector array.
        response_matrix : Union[str, OrbitResponseMatrixData]
            Orbit response matrix or path to a serialized matrix.
        rf_plant_name : Optional[str]
            Optional RF plant used for RF orbit correction.
        singular_values : Optional[int]
            Common number of singular values retained for both planes.
        singular_values_H : Optional[int]
            Number of horizontal singular values retained.
        singular_values_V : Optional[int]
            Number of vertical singular values retained.
        virtual_target : float
            Target value for virtual orbit correction.
        """
        super().__init__(name)

        self.bpm_array_name = bpm_array_name
        self.hcorr_array_name = hcorr_array_name
        self.vcorr_array_name = vcorr_array_name
        self._pySC_response_matrix = None
        self.rf_plant_name = rf_plant_name
        self.virtual_target = virtual_target

        if singular_values is None:
            if singular_values_H is None or singular_values_V is None:
                raise PyAMLException(
                    "Either `singular_values` or `singular_values_H` and `singular_values_V` must be provided."
                )
            self.singular_values_H = singular_values_H
            self.singular_values_V = singular_values_V
        else:
            if singular_values_H is not None or singular_values_V is not None:
                raise PyAMLException(
                    "Either `singular_values` or `singular_values_H` and `singular_values_V` must be provided, not both."
                )
            self.singular_values_H = singular_values
            self.singular_values_V = singular_values

        # If the configuration response matrix is a filename, load it
        if type(response_matrix) is str:
            try:
                self._response_matrix = OrbitResponseMatrixData.load(response_matrix)
            except Exception as e:
                logger.warning(f"Loading {response_matrix} failed {str(e)}")
                self._response_matrix = None

        # Converts to self._pySC_response_matrix
        if self._response_matrix:
            self._set_response_matrix(self._response_matrix)

        self._hcorr: MagnetArray = None
        self._vcorr: MagnetArray = None
        self._hvcorr: MagnetArray = None
        self._rf_plant: RFPlant = None

    def load(self, load_path: Path):
        """
        Dynamically loads a response matrix.

        Parameters
        ----------
        load_path : Path
            Filename of the :class:`~.OrbitResponseMatrixData` to load
        """
        self._response_matrix = OrbitResponseMatrixData.load(load_path)
        self._set_response_matrix(self.response_matrix)

    def _set_response_matrix(self, mat):
        """
        Configure the pySC response matrix from PyAML response data.

        The PyAML variable and observable fields are renamed to the names
        expected by pySC, including their horizontal and vertical plane
        metadata. The original PyAML model is retained for later access.

        Parameters
        ----------
        mat : OrbitResponseMatrixData
            Orbit response-matrix data containing the matrix, names, and
            plane metadata.
        """
        m = asdict(mat)
        m["input_names"] = m.pop("variable_names")
        m["output_names"] = m.pop("observable_names")
        m["input_planes"] = m.pop("variable_planes")
        m["output_planes"] = m.pop("observable_planes")
        m.pop("type", None)
        self._response_matrix = mat
        self._pySC_response_matrix = pySC_ResponseMatrix.model_validate(m)

    @property
    def response_matrix(self) -> OrbitResponseMatrixData | None:
        """
        Return the response matrix if it has been loaded None otherwise
        """
        return self._response_matrix

    def correct(
        self,
        plane: Optional[Literal["H", "V"]] = None,
        gain: float = 1.0,
        gain_H: Optional[float] = None,
        gain_V: Optional[float] = None,
        gain_RF: Optional[float] = None,
        singular_values_H: Optional[int] = None,
        singular_values_V: Optional[int] = None,
        reference: Optional[np.ndarray] = None,
        rf: bool = False,
        virtual_target: Optional[float] = None,
    ):
        """
        Perform orbit correction using the configured response matrix and corrector
        arrays.

        Parameters
        ----------
        reference : optional
            Optional reference orbit to correct towards. If not specified, corrects
            to zero orbit.
        gain : float, default 1.0
            Global gain applied to all corrector kicks if per-plane gains are not
            specified.
        plane : {'H', 'V'}, optional
            Plane to correct. If 'H', only horizontal correction is performed.
            If 'V', only vertical correction is performed.
            If None (default), both planes are corrected.
        gain_H : float, optional
            Gain for the horizontal plane. Overrides `gain` for H-plane if specified.
        gain_V : float, optional
            Gain for the vertical plane. Overrides `gain` for V-plane if specified.
        gain_RF : optional
            Gain for the correction with the rf frequency. If not specified,
            the gain of the horizontal plane is used.
        singular_values_H : int, optional
            Number of singular values to use for SVD decomposition in the horizontal
            plane. If not specified, uses the default or configured value.
        singular_values_V : int, optional
            Number of singular values to use for SVD decomposition in the vertical
            plane. If not specified, uses the default or configured value.
        rf : bool, default False,
            If set to true, the rf_response will also be used in the response matrix
            for correction of the horizontal orbit. Only takes into effect if plane is
            None or if plane = 'H'.
        """

        if self._pySC_response_matrix is None:
            raise PyAMLException(f"{self.get_name()} does not have a response_matrix.")

        interface = pySCInterface(
            element_holder=self.peer,
            bpm_array_name=self.bpm_array_name,
        )

        if singular_values_H is not None:
            svH = singular_values_H
        else:
            svH = self.singular_values_H

        if singular_values_V is not None:
            svV = singular_values_V
        else:
            svV = self.singular_values_V

        if virtual_target is None:
            virtual_target = self.virtual_target

        if plane is None or plane == "H":
            trims_h = orbit_correction(
                interface=interface,
                response_matrix=self._pySC_response_matrix,
                method="svd_values",
                parameter=svH,
                virtual=True,
                apply=False,
                plane="H",
                reference=reference,
                rf=rf,
                virtual_target=virtual_target,
            )

        if plane is None or plane == "V":
            trims_v = orbit_correction(
                interface=interface,
                response_matrix=self._pySC_response_matrix,
                method="svd_values",
                parameter=svV,
                virtual=False,
                apply=False,
                plane="V",
                reference=reference,
                rf=False,
            )

        eff_gain_H = gain_H if gain_H is not None else gain
        eff_gain_V = gain_V if gain_V is not None else gain

        # take care of rf trim
        rf_flag = rf and (plane is None or plane == "H")
        if rf_flag:
            if self._rf_plant is None:
                raise PyAMLException("RF plant is not defined!")
            eff_gain_RF = gain_RF if gain_RF is not None else eff_gain_H
            ## pySC returns with an 'rf' entry into the dictionary if rf=True
            rf_trim = eff_gain_RF * trims_h["rf"]
            del trims_h["rf"]

        # collect all trims and apply gain
        if plane is None:
            for trim in trims_h:
                trims_h[trim] *= eff_gain_H
            for trim in trims_v:
                trims_v[trim] *= eff_gain_V
            trims = {**trims_h, **trims_v}
            corr_array = self._hvcorr
        elif plane == "H":
            for trim in trims_h:
                trims_h[trim] *= eff_gain_H
            trims = trims_h
            corr_array = self._hcorr
        elif plane == "V":
            for trim in trims_v:
                trims_v[trim] *= eff_gain_V
            trims = trims_v
            corr_array = self._vcorr

        corrector_names = corr_array.names()
        corrector_to_index = {name: idx for idx, name in enumerate(corrector_names)}
        data_to_send = corr_array.strengths.get()
        for name in trims.keys():
            idx = corrector_to_index.get(name, None)
            if idx is None:
                raise PyAMLException(
                    f"Corrector {name} not found in the magnet array for orbit corr. "
                    "Possible inconcistency between corrector arrays and "
                    "response matrix."
                )
            data_to_send[idx] += trims[name]

        # send trims
        corr_array.strengths.set(data_to_send)
        if rf_flag:
            rf_frequency = self._rf_plant.frequency.get()
            self._rf_plant.frequency.set(rf_frequency + rf_trim)

        return

    def set_weight(self, name: str, weight: float, plane: Optional[Literal["H", "V"]] = None) -> None:
        """
        Set the weight of a response-matrix input or output.

        Weights affect the relative importance of variables and observables
        during orbit correction. A plane is required when ``name`` occurs in
        more than one plane.

        Parameters
        ----------
        name : str
            Variable or observable name whose weight should be changed.
        weight : float
            New weight applied during orbit correction.
        plane : Optional[Literal['H', 'V']]
            Optional plane selector, either ``"H"`` or ``"V"``.

        Returns
        -------
        None
            This method does not return a value.
        """
        self._pySC_response_matrix.set_weight(name, weight, plane=plane)
        return

    def set_virtual_weight(self, weight: float) -> None:
        """
        Set the weight of the virtual orbit target.

        Parameters
        ----------
        weight : float
            New virtual-target weight used during correction.

        Returns
        -------
        None
            This method does not return a value.
        """
        self._pySC_response_matrix.virtual_weight = weight
        return

    def set_rf_weight(self, weight: float) -> None:
        """
        Set the weight of the RF-frequency correction variable.

        Parameters
        ----------
        weight : float
            New RF-variable weight used during correction.

        Returns
        -------
        None
            This method does not return a value.
        """
        self._pySC_response_matrix.rf_weight = weight
        return

    def get_weight(self, name: str, plane: Optional[Literal["H", "V"]] = None) -> float:
        """
        Return the response-matrix weight for a named input or output.

        If the name is present in multiple planes, pass ``plane`` to select
        the desired weight.

        Parameters
        ----------
        name : str
            Variable or observable name whose weight should be returned.
        plane : Optional[Literal['H', 'V']]
            Optional plane selector, either ``"H"`` or ``"V"``.

        Returns
        -------
        float
            Configured response-matrix weight.
        """
        names = []
        planes = []
        weights = []

        inames = self._pySC_response_matrix.input_names
        iplanes = self._pySC_response_matrix.input_planes
        iweights = self._pySC_response_matrix.input_weights
        for iname, iplane, iw in zip(inames, iplanes, iweights, strict=True):
            if name == iname:
                if plane is None or plane == iplane:
                    names.append(iname)
                    planes.append(iplane)
                    weights.append(iw)

        onames = self._pySC_response_matrix.output_names
        oplanes = self._pySC_response_matrix.output_planes
        oweights = self._pySC_response_matrix.output_weights
        for oname, oplane, ow in zip(onames, oplanes, oweights, strict=True):
            if name == oname:
                if plane is None or plane == oplane:
                    names.append(oname)
                    planes.append(oplane)
                    weights.append(ow)

        if len(weights) == 1:
            return weights[0]
        else:
            raise PyAMLException(f"More than one weight found, please select plane. {names=}, {planes=}, {weights=}")

    def get_virtual_weight(self) -> float:
        """Return the configured virtual-orbit target weight."""
        return self._pySC_response_matrix.virtual_weight

    def get_rf_weight(self) -> float:
        """Return the configured RF-frequency correction weight."""
        return self._pySC_response_matrix.rf_weight

    def post_init(self):
        """Bind orbit corrector and RF handles after attachment."""
        self._hcorr = self.peer.magnets.get(self.hcorr_array_name)
        self._vcorr = self.peer.magnets.get(self.vcorr_array_name)
        hvElts = []
        hvElts.extend(self._hcorr)
        hvElts.extend(self._vcorr)
        self._hvcorr = MagnetArray("", hvElts)
        if self.rf_plant_name is not None:
            self._rf_plant = self.peer.rf.get(self.rf_plant_name)
