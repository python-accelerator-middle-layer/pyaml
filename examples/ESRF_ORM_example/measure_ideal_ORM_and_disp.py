import json
from pathlib import Path

import numpy as np

from pyaml.accelerator import Accelerator
from pyaml.tuning_tools.dispersion import ConfigModel as Disp_ConfigModel
from pyaml.tuning_tools.dispersion import Dispersion
from pyaml.tuning_tools.orbit_response_matrix import ConfigModel as ORM_ConfigModel
from pyaml.tuning_tools.orbit_response_matrix import OrbitResponseMatrix

parent_folder = Path(__file__).parent
config_path = parent_folder.parent.parent.joinpath(
    "tests", "config", "EBSOrbit.yaml"
).resolve()
sr = Accelerator.load(config_path)
element_holder = sr.design

orm = OrbitResponseMatrix(
    cfg=ORM_ConfigModel(
        bpm_array_name="BPM",
        hcorr_array_name="HCorr",
        vcorr_array_name="VCorr",
        corrector_delta=1e-6,
    ),
    element_holder=element_holder,
)

orm.measure()

orm_data = orm.get()

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
rf_response = (
    dispersion_data["frequency_response_x"] + dispersion_data["frequency_response_y"]
)

ideal_ORM_data = {
    "matrix": orm_data["matrix"],
    "input_names": orm_data["input_names"],
    "output_names": orm_data["output_names"],
    "rf_response": rf_response,
}

json.dump(ideal_ORM_data, open("ideal_orm_disp.json", "w"), indent=4)
