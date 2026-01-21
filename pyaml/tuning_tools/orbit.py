import logging
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Optional, Union

try:
    from typing import Self  # Python 3.11+
except ImportError:
    from typing_extensions import Self  # Python 3.10 and earlier


from pydantic import ConfigDict

if TYPE_CHECKING:
    from ..common.element_holder import ElementHolder
from pySC import ResponseMatrix as pySC_ResponseMatrix
from pySC.apps import orbit_correction

from ..arrays.magnet_array import MagnetArray
from ..common.element import Element, ElementConfigModel
from ..common.exception import PyAMLException
from ..configuration.factory import Factory
from ..configuration.fileloader import get_path, load
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
    response_matrix: Union[str, ResponseMatrix]


class Orbit(Element):
    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg.name)
        self._cfg = cfg
        self.bpm_array_name = cfg.bpm_array_name
        self.hcorr_array_name = cfg.hcorr_array_name
        self.vcorr_array_name = cfg.vcorr_array_name
        self.singular_values = cfg.singular_values

        if type(cfg.response_matrix) is str:
            response_matrix_filename = cfg.response_matrix
            # assigns self.response_matrix
            if Path(response_matrix_filename).exists():
                self.load_response_matrix(response_matrix_filename)
            else:
                logger.warning(f"{response_matrix_filename} does not exist.")
                self.response_matrix = None
        else:
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
        if self.response_matrix is None:
            raise PyAMLException(f"{self.get_name()} does not have a response_matrix.")

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
            data_to_send[idx] += trims[name] * gain

        corr_array.strengths.set(data_to_send)
        return

    def post_init(self):
        self._hcorr = self._peer.get_magnets(self._cfg.hcorr_array_name)
        self._vcorr = self._peer.get_magnets(self._cfg.vcorr_array_name)
        hvElts = []
        hvElts.extend(self._hcorr)
        hvElts.extend(self._vcorr)
        self._hvcorr = MagnetArray("", hvElts)

    def attach(self, peer: "ElementHolder") -> Self:
        """
        Create a new reference to attach this Orbit object to a simulator
        or a control system.
        """
        obj = self.__class__(self._cfg)
        obj._peer = peer
        return obj

    def load_response_matrix(self, filename: str) -> None:
        path = Path(filename)
        config_dict = load(str(path.resolve()))
        rm = Factory.depth_first_build(config_dict, ignore_external=False)
        self.response_matrix = pySC_ResponseMatrix.model_validate(rm._cfg.model_dump())
        return None
