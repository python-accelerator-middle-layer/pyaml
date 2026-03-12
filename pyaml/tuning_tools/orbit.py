import logging
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Optional, Union

try:
    from typing import Self  # Python 3.11+
except ImportError:
    from typing_extensions import Self  # Python 3.10 and earlier

import numpy as np
from pydantic import ConfigDict

if TYPE_CHECKING:
    from ..common.element_holder import ElementHolder
from pySC import ResponseMatrix as pySC_ResponseMatrix
from pySC.apps import orbit_correction

from ..arrays.magnet_array import MagnetArray
from ..common.element import Element, ElementConfigModel
from ..common.exception import PyAMLException
from ..external.pySC_interface import pySCInterface
from ..rf.rf_plant import RFPlant
from .orbit_response_matrix_data import OrbitResponseMatrixData

logger = logging.getLogger(__name__)
logging.getLogger("pyaml.external.pySC").setLevel(logging.WARNING)

PYAMLCLASS = "Orbit"


class ConfigModel(ElementConfigModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    bpm_array_name: str
    hcorr_array_name: str
    vcorr_array_name: str
    rf_plant_name: Optional[str] = None
    singular_values: Optional[int] = None
    singular_values_H: Optional[int] = None
    singular_values_V: Optional[int] = None
    virtual_target: float = 0
    response_matrix: Union[str, OrbitResponseMatrixData]


class Orbit(Element):
    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg.name)
        self._cfg = cfg
        self.bpm_array_name = cfg.bpm_array_name
        self.hcorr_array_name = cfg.hcorr_array_name
        self.vcorr_array_name = cfg.vcorr_array_name
        self._pySC_response_matrix = None

        self.virtual_target = cfg.virtual_target

        if cfg.singular_values is None:
            if cfg.singular_values_H is None or cfg.singular_values_V is None:
                raise PyAMLException(
                    "Either `singular_values` or `singular_values_H` and "
                    "`singular_values_V` must be provided."
                )
            self.singular_values_H = cfg.singular_values_H
            self.singular_values_V = cfg.singular_values_V
        else:
            if cfg.singular_values_H is not None or cfg.singular_values_V is not None:
                raise PyAMLException(
                    "Either `singular_values` or `singular_values_H` and "
                    "`singular_values_V` must be provided, not both."
                )
            self.singular_values_H = cfg.singular_values
            self.singular_values_V = cfg.singular_values

        # If the configuration response matrix is a filename, load it
        if type(cfg.response_matrix) is str:
            try:
                cfg.response_matrix = OrbitResponseMatrixData.load(cfg.response_matrix)
            except Exception as e:
                logger.warning(f"{str(e)}")
                cfg.response_matrix = None

        # assigns self._pySC_response_matrix
        if cfg.response_matrix:
            self._pySC_response_matrix = pySC_ResponseMatrix.model_validate(
                cfg.response_matrix._cfg.model_dump()
            )

        self._hcorr: MagnetArray = None
        self._vcorr: MagnetArray = None
        self._hvcorr: MagnetArray = None
        self._rf_plant: RFPlant = None

    @property
    def reponse_matrix(self) -> OrbitResponseMatrixData | None:
        return self._cfg.response_matrix

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
            element_holder=self._peer,
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

    def set_weight(
        self, name: str, weight: float, plane: Optional[Literal["H", "V"]] = None
    ) -> None:
        self._pySC_response_matrix.set_weight(name, weight, plane=plane)
        return

    def set_virtual_weight(self, weight: float) -> None:
        self._pySC_response_matrix.virtual_weight = weight
        return

    def set_rf_weight(self, weight: float) -> None:
        self._pySC_response_matrix.rf_weight = weight
        return

    def get_weight(self, name: str, plane: Optional[Literal["H", "V"]] = None) -> float:
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
            raise PyAMLException(
                "More than one weight found, please select plane. "
                f"{names=}, {planes=}, {weights=}"
            )

    def get_virtual_weight(self) -> float:
        return self._pySC_response_matrix.virtual_weight

    def get_rf_weight(self) -> float:
        return self._pySC_response_matrix.rf_weight

    def post_init(self):
        self._hcorr = self._peer.get_magnets(self._cfg.hcorr_array_name)
        self._vcorr = self._peer.get_magnets(self._cfg.vcorr_array_name)
        hvElts = []
        hvElts.extend(self._hcorr)
        hvElts.extend(self._vcorr)
        self._hvcorr = MagnetArray("", hvElts)
        if self._cfg.rf_plant_name is not None:
            self._rf_plant = self._peer.get_rf_plant(self._cfg.rf_plant_name)

    def attach(self, peer: "ElementHolder") -> Self:
        """
        Create a new reference to attach this Orbit object to a simulator
        or a control system.
        """
        obj = self.__class__(self._cfg)
        obj._peer = peer
        return obj
