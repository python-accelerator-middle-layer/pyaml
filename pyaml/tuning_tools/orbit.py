import logging
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Optional, Self

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from ..common.element_holder import ElementHolder
# from ..external.pySC.pySC import ResponseMatrix as pySC_ResponseMatrix
from ..arrays.magnet_array import MagnetArray
from ..common.element import Element, ElementConfigModel
from ..common.exception import PyAMLException
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
            trims = {**trims_h, **trims_v}
            corr_array = self._hvcorr
        elif plane == "H":
            trims = trims_h
            corr_array = self._hcorr
        elif plane == "V":
            trims = trims_v
            corr_array = self._vcorr

        corrector_was_used = {key: False for key in trims.keys()}
        corrector_names = corr_array.names()
        data_to_send = corr_array.strengths.get()
        for idx, name in enumerate(corrector_names):
            data_to_send[idx] += trims[name] * gain
            corrector_was_used[name] = True

        # check that all corrector trims will be sent
        for key in trims.keys():
            if not corrector_was_used[key]:
                raise PyAMLException(
                    f"Corrector {key} was not used in the orbit correction. "
                    "There is an inconcistency between corrector arrays and "
                    "response matrix."
                )

        corr_array.strengths.set(data_to_send)
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
        return obj
