import logging
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Optional, Self

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from ..common.element_holder import ElementHolder
# from ..external.pySC.pySC import ResponseMatrix as pySC_ResponseMatrix
from ..arrays.magnet_array import MagnetArray
from ..common.element import Element, ElementConfigModel
from ..external.pySC.pySC import ResponseMatrix as pySC_ResponseMatrix
from ..external.pySC.pySC.apps import orbit_correction
from ..external.pySC_interface import pySCInterface
from .response_matrix import ResponseMatrix

logger = logging.getLogger(__name__)
logging.getLogger("pyaml.external.pySC").setLevel(logging.WARNING)

PYAMLCLASS = "Orbit"


class ConfigModel(ElementConfigModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    bpm_array_name: str
    hcorr_array_name: str
    vcorr_array_name: str
    singular_values: int
    response_matrix: Optional[ResponseMatrix]


class Orbit(Element):
    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg.name)
        self._cfg = cfg

        self.bpm_array_name = cfg.bpm_array_name
        self.hcorr_array_name = cfg.hcorr_array_name
        self.vcorr_array_name = cfg.vcorr_array_name
        self.singular_values = cfg.singular_values
        self.response_matrix = pySC_ResponseMatrix.model_validate(
            cfg.response_matrix._cfg.model_dump()
        )
        self._hcorr: MagnetArray = None
        self._vcorr: MagnetArray = None
        self._hvcorr: MagnetArray = None

    def correct(
        self,
        reference=None,
        gain: float = 1.0,
        plane: Optional[Literal["H", "V"]] = None,
    ):
        interface = pySCInterface(
            element_holder=self._peer,
            bpm_array_name=self.bpm_array_name,
            hcorr_array_name=self.hcorr_array_name,
            vcorr_array_name=self.vcorr_array_name,
        )

        if plane is None or plane == "H":
            trims_h = orbit_correction(
                interface=interface,
                response_matrix=self.response_matrix,
                method="svd_values",
                parameter=self.singular_values,
                zerosum=True,
                apply=False,
                plane="H",
                reference=reference,
            )

        if plane is None or plane == "V":
            trims_v = orbit_correction(
                interface=interface,
                response_matrix=self.response_matrix,
                method="svd_values",
                parameter=self.singular_values,
                zerosum=False,
                apply=False,
                plane="V",
                reference=reference,
            )

        if plane is None:
            data_to_send_hv = self._hvcorr.strengths.get()
            for idx, name in enumerate(trims_h.keys()):
                data_to_send_hv[idx] += trims_h[name] * gain
            l = len(trims_h.keys())
            for idx, name in enumerate(trims_v.keys()):
                data_to_send_hv[idx + l] += trims_v[name] * gain
            self._hvcorr.strengths.set(data_to_send_hv)
        elif plane == "H":
            data_to_send_h = self._hcorr.strengths.get()
            for idx, name in enumerate(trims_h.keys()):
                data_to_send_h[idx] += trims_h[name] * gain
            self._hcorr.strengths.set(data_to_send_h)
        elif plane == "V":
            data_to_send_v = self._vcorr.strengths.get()
            for idx, name in enumerate(trims_v.keys()):
                data_to_send_v[idx] += trims_v[name] * gain
            self._vcorr.strengths.set(data_to_send_v)

        return

    def post_init(self):
        self._hcorr = self._peer.get_magnets(self._cfg.hcorr_array_name)
        self._vcorr = self._peer.get_magnets(self._cfg.vcorr_array_name)
        hvElts = []
        hvElts.extend(self._hcorr)
        hvElts.extend(self._vcorr)
        self._hvcorr = MagnetArray("HVCorr", hvElts)

    def attach(self, peer: "ElementHolder") -> Self:
        """
        Create a new reference to attach this Orbit object to a simulator
        or a control system.
        """
        obj = self.__class__(self._cfg)
        obj._peer = peer
        obj.response_matrix = self.response_matrix  # Copy only ref
        return obj
