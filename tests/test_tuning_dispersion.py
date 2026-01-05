import logging
from pathlib import Path

import numpy as np

from pyaml.accelerator import Accelerator
from pyaml.configuration.factory import Factory
from pyaml.tuning_tools.dispersion import ConfigModel as Disp_ConfigModel
from pyaml.tuning_tools.dispersion import Dispersion


def test_tuning_orm():
    logging.getLogger("pyaml.tuning_tools").setLevel(logging.WARNING)

    parent_folder = Path(__file__).parent
    config_path = parent_folder.joinpath("config", "EBSOrbit.yaml").resolve()
    sr = Accelerator.load(config_path)
    element_holder = sr.design

    dispersion = Dispersion(
        cfg=Disp_ConfigModel(
            bpm_array_name="BPM",
            rf_plant_name="RF",
            frequency_delta=10,
        ),
        element_holder=element_holder,
    )

    dispersion.measure()
    dispersion_data = dispersion.get()

    bpms = element_holder.get_bpms("BPM")

    assert len(dispersion_data["frequency_response_x"]) == len(bpms)
    assert len(dispersion_data["frequency_response_y"]) == len(bpms)

    Factory.clear()
