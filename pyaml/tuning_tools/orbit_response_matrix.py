import logging
from pathlib import Path
from typing import Callable, List, Optional, Self

import pySC
from pydantic import BaseModel, ConfigDict
from pySC.apps import measure_ORM
from pySC.apps.codes import ResponseCode

from ..common.constants import ACTION_APPLY, ACTION_MEASURE, ACTION_RESTORE
from ..common.element import Element, ElementConfigModel
from ..common.element_holder import ElementHolder
from ..common.exception import PyAMLException
from ..external.pySC_interface import pySCInterface

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


class OrbitResponseMatrix(Element):
    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg.name)
        self._cfg = cfg

        self.bpm_array_name = cfg.bpm_array_name
        self.hcorr_array_name = cfg.hcorr_array_name
        self.vcorr_array_name = cfg.vcorr_array_name
        self.corrector_delta = cfg.corrector_delta
        self.latest_measurement = None

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
                f"Measuring correctors from the default arrays: "
                f"{self.hcorr_array_name} and {self.vcorr_array_name}."
            )
            hcorrector_names = element_holder.get_magnets(self.hcorr_array_name).names()
            vcorrector_names = element_holder.get_magnets(self.vcorr_array_name).names()
            corrector_names = hcorrector_names + vcorrector_names
        else:
            all_hcorrector_names = element_holder.get_magnets(
                self.hcorr_array_name
            ).names()
            all_vcorrector_names = element_holder.get_magnets(
                self.vcorr_array_name
            ).names()
            hcorrector_names = [
                corr for corr in corrector_names if corr in all_hcorrector_names
            ]
            vcorrector_names = [
                corr for corr in corrector_names if corr in all_vcorrector_names
            ]

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
                if callback and not callback(ACTION_APPLY, callback_data):
                    if aborted:
                        break
            elif code is ResponseCode.AFTER_GET:
                if callback and not callback(ACTION_MEASURE, callback_data):
                    aborted = True
                    break
            elif code is ResponseCode.AFTER_RESTORE:
                logger.info(f"Measured response of {measurement.last_input}.")
                if callback and not callback(ACTION_RESTORE, callback_data):
                    aborted = True
                    break

        if aborted:
            logger.warning("Measurement aborted! Settings have not been restored.")
            return

        response_data = measurement.response_data  # contains also pre-processed data
        response_data.output_names = element_holder.get_bpms(
            self.bpm_array_name
        ).names()
        self.latest_measurement = response_data.model_dump()

        inputs_plane = []
        for corr in corrector_names:
            if corr in hcorrector_names:
                inputs_plane.append("H")
            elif corr in vcorrector_names:
                inputs_plane.append("V")
        self.latest_measurement["inputs_plane"] = inputs_plane

        len_b = len(response_data.output_names)
        self.latest_measurement["outputs_plane"] = ["H"] * len_b + ["V"] * len_b

    def get(self):
        return self.latest_measurement

    def save(self, save_path: Path, with_type: str = "json"):
        # should we make a general pyaml saving/loading function for data?
        if with_type == "json":
            import json

            data = self.latest_measurement
            json.dump(data, open(save_path, "w"), indent=4)
        elif with_type == "yaml":
            import yaml

            data = self.latest_measurement
            yaml.safe_dump(data, open(save_path, "w"))
        elif with_type == "npz":
            import numpy as np

            data = self.latest_measurement
            np.savez(save_path.resolve(), **data)
        else:
            raise PyAMLException(f"ERROR: Unknown file type to save as: {with_type}.")

    def attach(self, peer: "ElementHolder") -> Self:
        """
        Create a new reference to attach this OrbitResponseMatrix object to a simulator
        or a control system.
        """
        obj = self.__class__(self._cfg)
        obj._peer = peer
        return obj
