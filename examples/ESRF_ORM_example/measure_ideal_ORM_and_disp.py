import json
from pathlib import Path

import numpy as np

from pyaml.accelerator import Accelerator

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
    "input_planes": orm_data["input_planes"],
    "output_planes": orm_data["output_planes"],
    "rf_response": rf_response,
}

json.dump(ideal_ORM_data, open("ideal_orm_disp.json", "w"))
