import logging
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from ..common.element_holder import ElementHolder
from ..external.pySC.pySC.apps import measure_dispersion
from ..external.pySC_interface import pySCInterface

logger = logging.getLogger(__name__)

PYAMLCLASS = "OrbitResponseMatrix"


class ConfigModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    bpm_array_name: str
    rf_plant_name: str
    frequency_delta: float


class Dispersion(object):
    def __init__(self, element_holder: ElementHolder, cfg: ConfigModel):
        self._cfg = cfg

        self.element_holder = element_holder
        self.bpm_array_name = cfg.bpm_array_name
        self.rf_plant_name = cfg.rf_plant_name
        self.frequency_delta = cfg.frequency_delta
        self.latest_measurement = None

    def measure(self):
        interface = pySCInterface(
            element_holder=self.element_holder,
            bpm_array_name=self.bpm_array_name,
            rf_plant_name=self.rf_plant_name,
        )

        generator = measure_dispersion(
            interface=interface,
            delta=self.frequency_delta,
            skip_save=True,
        )

        _, measurement = next(generator)
        for _, _ in generator:
            pass

        dispersion_data = measurement.dispersion_data
        # contains also pre-processed data

        # dispersion_data.output_names = self.element_holder.get_bpms(
        #     self.bpm_array_name
        # ).names()
        self.latest_measurement = dispersion_data.model_dump()

    def get(self):
        return self.latest_measurement
