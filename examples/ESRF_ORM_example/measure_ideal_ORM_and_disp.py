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

ebs = sr.design

ebs.orm.measure()
orm_data = ebs.orm.get()

ebs.dispersion.measure()
dispersion_data = ebs.dispersion.get()

rf_response = (
    dispersion_data["frequency_response_x"] + dispersion_data["frequency_response_y"]
)

ideal_ORM_data = {
    "type": "pyaml.tuning_tools.response_matrix",
    "matrix": orm_data["matrix"],
    "input_names": orm_data["input_names"],
    "output_names": orm_data["output_names"],
    "inputs_plane": orm_data["inputs_plane"],
    "outputs_plane": orm_data["outputs_plane"],
    "rf_response": rf_response,
}

json.dump(ideal_ORM_data, open("ideal_orm_disp.json", "w"))
