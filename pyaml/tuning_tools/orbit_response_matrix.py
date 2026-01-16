import logging
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from ..common.element_holder import ElementHolder
from ..common.exception import PyAMLException
from ..external.pySC import pySC
from ..external.pySC.pySC.apps import measure_ORM
from ..external.pySC.pySC.apps.codes import ResponseCode
from ..external.pySC_interface import pySCInterface

logger = logging.getLogger(__name__)

PYAMLCLASS = "OrbitResponseMatrix"


class ConfigModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    bpm_array_name: str
    hcorr_array_name: str
    vcorr_array_name: str
    corrector_delta: float


class OrbitResponseMatrix(object):
    def __init__(self, element_holder: ElementHolder, cfg: ConfigModel):
        self._cfg = cfg

        self.element_holder = element_holder
        self.bpm_array_name = cfg.bpm_array_name
        self.hcorr_array_name = cfg.hcorr_array_name
        self.vcorr_array_name = cfg.vcorr_array_name
        self.corrector_delta = cfg.corrector_delta
        self.latest_measurement = None

    def measure(self, corrector_names: Optional[List[str]] = None):
        interface = pySCInterface(
            element_holder=self.element_holder,
            bpm_array_name=self.bpm_array_name,
            hcorr_array_name=self.hcorr_array_name,
            vcorr_array_name=self.vcorr_array_name,
        )

        if corrector_names is None:
            logger.info(
                f"Measuring correctors from the default arrays: "
                f"{self.hcorr_array_name} and {self.vcorr_array_name}."
            )
            hcorrector_names = self.element_holder.get_magnets(
                self.hcorr_array_name
            ).names()
            vcorrector_names = self.element_holder.get_magnets(
                self.vcorr_array_name
            ).names()
            corrector_names = hcorrector_names + vcorrector_names

        generator = measure_ORM(
            interface=interface,
            corrector_names=corrector_names,
            delta=self.corrector_delta,
            skip_save=True,
        )

        pySC.disable_pySC_rich()
        for code, measurement in generator:
            if code is ResponseCode.MEASURING:
                logger.info(f"Measured response of {measurement.last_input}.")

        response_data = measurement.response_data  # contains also pre-processed data
        response_data.output_names = self.element_holder.get_bpms(
            self.bpm_array_name
        ).names()
        self.latest_measurement = response_data.model_dump()

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
