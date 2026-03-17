import logging
from pathlib import Path
from typing import Callable, List, Optional, Self

import pySC
from pydantic import ConfigDict
from pySC.apps import measure_ORM
from pySC.apps.codes import ResponseCode

from ..common.constants import Action
from ..common.element import ElementConfigModel
from ..external.pySC_interface import pySCInterface
from .measurement_tool import MeasurementTool
from .orbit_response_matrix_data import ConfigModel as OrbitResponseMatrixDataConfigModel
from .orbit_response_matrix_data import OrbitResponseMatrixData

logger = logging.getLogger(__name__)

PYAMLCLASS = "OrbitResponseMatrix"


class ConfigModel(ElementConfigModel):
    """
    Configuration model for orbit response matrix measurement

    Parameters
    ----------
    bpm_array_name : str
        BPM array name
    hcorr_array_name : str
        Horizontal corrector array name
    vcorr_array_name : str
        Vertical corrector array name
    corrector_delta : float
        Corrector delta for measurement
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    bpm_array_name: str
    hcorr_array_name: str
    vcorr_array_name: str
    corrector_delta: float


class OrbitResponseMatrix(MeasurementTool):
    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg.name)
        self._cfg = cfg

        self.bpm_array_name = cfg.bpm_array_name
        self.hcorr_array_name = cfg.hcorr_array_name
        self.vcorr_array_name = cfg.vcorr_array_name
        self.corrector_delta = cfg.corrector_delta

    def measure(
        self,
        corrector_names: Optional[List[str]] = None,
        set_wait_time: float = 0,
        callback: Optional[Callable] = None,
    ):
        """
        Measure orbit response matrix

        Parameters
        ----------
        callback : Callable, optional
            example: callback(action:int, callback_data: 'Complicated struct')
            callback is executed after each strength setting and after each orbit
            reading.
            If the callback returns false, then the process is aborted.
        """
        element_holder = self._peer
        interface = pySCInterface(
            element_holder=element_holder,
            bpm_array_name=self.bpm_array_name,
        )
        interface.set_wait_time = set_wait_time

        if corrector_names is None:
            logger.info(
                f"Measuring correctors from the default arrays: {self.hcorr_array_name} and {self.vcorr_array_name}."
            )
            hcorrector_names = element_holder.get_magnets(self.hcorr_array_name).names()
            vcorrector_names = element_holder.get_magnets(self.vcorr_array_name).names()
            corrector_names = hcorrector_names + vcorrector_names

        generator = measure_ORM(
            interface=interface,
            corrector_names=corrector_names,
            delta=self.corrector_delta,
            skip_save=True,
        )

        pySC.disable_pySC_rich()
        aborted = False
        for code, measurement in generator:
            callback_data = measurement.response_data  # to be defined better
            if code is ResponseCode.AFTER_SET:
                if not self.send_callback(Action.APPLY, callback, callback_data):
                    if aborted:
                        break
            elif code is ResponseCode.AFTER_GET:
                if not self.send_callback(Action.MEASURE, callback, callback_data):
                    aborted = True
                    break
            elif code is ResponseCode.AFTER_RESTORE:
                logger.info(f"Measured response of {measurement.last_input}.")
                if not self.send_callback(Action.RESTORE, callback, callback_data):
                    aborted = True
                    break

        if aborted:
            logger.warning("Measurement aborted! Settings have not been restored.")
            return

        orm_data = self._pySC_response_data_to_ORMData(measurement.response_data.model_dump())
        self.latest_measurement = orm_data.model_dump()

    def _pySC_response_data_to_ORMData(self, data: dict) -> OrbitResponseMatrixDataConfigModel:
        # all metadata is discarded here. Should we keep something?

        element_holder = self._peer
        all_hcorrector_names = element_holder.get_magnets(self.hcorr_array_name).names()
        all_vcorrector_names = element_holder.get_magnets(self.vcorr_array_name).names()
        variable_planes = []
        for corr in data["input_names"]:
            if corr in all_hcorrector_names:
                variable_planes.append("H")
            elif corr in all_vcorrector_names:
                variable_planes.append("V")

        bpm_names = element_holder.get_bpms(self.bpm_array_name).names()
        # This is because we assume always dual-plane bpms now.
        len_b = len(bpm_names)
        observable_names = bpm_names * 2
        observable_planes = ["H"] * len_b + ["V"] * len_b

        orm_data_model = {
            "matrix": data["matrix"],
            "variable_names": data["input_names"],
            "observable_names": observable_names,
            "rf_response": None,
            "variable_planes": variable_planes,
            "observable_planes": observable_planes,
        }

        orm_data = OrbitResponseMatrixDataConfigModel(**orm_data_model)
        return orm_data
