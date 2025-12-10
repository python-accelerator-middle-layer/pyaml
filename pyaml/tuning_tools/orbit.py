import logging
from pathlib import Path
from typing import Literal, Optional, Self, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from ..common.element_holder import ElementHolder
#from ..external.pySC.pySC import ResponseMatrix as pySC_ResponseMatrix
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

        #self.element_holder = element_holder
        self.bpm_array_name = cfg.bpm_array_name
        self.hcorr_array_name = cfg.hcorr_array_name
        self.vcorr_array_name = cfg.vcorr_array_name
        self.singular_values = cfg.singular_values
        self.response_matrix = pySC_ResponseMatrix.model_validate(
            cfg.response_matrix._cfg.model_dump()
        )

    def correct(
        self,
        reference=None,
        gain: float = 1.0,
        plane: Optional[Literal["H", "V"]] = None,
    ):
        interface = pySCInterface(
            element_holder=self.element_holder,
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

        # this is now the only place where interface.set_many and get_many are used.
        # if we can remove it from here then the pySCInterface will be even simpler.
        correctors = self.response_matrix.input_names
        data_to_send = interface.get_many(correctors)
        if plane is None or plane == "H":
            for name in trims_h.keys():
                data_to_send[name] += trims_h[name] * gain
        if plane is None or plane == "V":
            for name in trims_v.keys():
                data_to_send[name] += trims_v[name] * gain

        interface.set_many(data_to_send)

        return

    def attach(self, peer: "ElementHolder") -> Self:
        """
        Create a new reference to attach this Orbit object to a simulator
        or a control system.
        """
        obj = self.__class__(self._cfg)
        obj._peer = peer
        return obj
