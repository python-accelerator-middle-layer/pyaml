import json
from pathlib import Path

import numpy as np

from pyaml.accelerator import Accelerator

parent_folder = Path(__file__).parent
config_path = parent_folder.parent.parent.joinpath("tests", "config", "EBSOrbit.yaml").resolve()
sr = Accelerator.load(config_path)

ebs = sr.design

ebs.orm.measure()
orm_data = ebs.orm.get()

ebs.dispersion.measure()
dispersion_data = ebs.dispersion.get()

rf_response = dispersion_data["frequency_response_x"] + dispersion_data["frequency_response_y"]

orm_data["rf_response"] = rf_response

ebs.orm.save("ideal_orm_disp.json")
