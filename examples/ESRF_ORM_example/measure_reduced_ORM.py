import logging
from pathlib import Path

import numpy as np

from pyaml.accelerator import Accelerator
from pyaml.common.constants import ACTION_RESTORE
from pyaml.tuning_tools.orbit_response_matrix import ConfigModel as ORM_ConfigModel
from pyaml.tuning_tools.orbit_response_matrix import OrbitResponseMatrix

# disable printing during ORM measurement to illustrate callback.
logger = logging.getLogger("pyaml.tuning_tools.orbit_response_matrix").setLevel(
    logging.WARNING
)

parent_folder = Path(__file__).parent
config_path = parent_folder.parent.parent.joinpath(
    "tests", "config", "EBSOrbit.yaml"
).resolve()
sr = Accelerator.load(config_path)
ebs = sr.design
orm = ebs.orm

hcorr = ebs.get_magnets("HCorr")
vcorr = ebs.get_magnets("VCorr")
corrector_names = (
    hcorr["SJ2A*"].names()
    + hcorr["SF2A*"].names()
    + hcorr["SI2A*"].names()
    + vcorr["SJ2A*"].names()
    + vcorr["SF2A*"].names()
    + vcorr["SI2A*"].names()
)


def callback(action: int, cdata):
    if action == ACTION_RESTORE:
        i = cdata.last_number
        n_bpms = cdata.raw_up.shape[0] // 2
        n_correctors = cdata.raw_up.shape[1]
        corrector = cdata.last_input
        response = (cdata.raw_up[:, i] - cdata.raw_down[:, i]) / cdata.inputs_delta[i]
        std_x_resp = np.std(response[:n_bpms])
        std_y_resp = np.std(response[n_bpms:])
        print(
            f"[{i}/{n_correctors}], Measured response of {corrector}: "
            f"r.m.s H.: {std_x_resp:.2f} mm/mrad, r.m.s. V: {std_y_resp:.2f} mm/mrad"
        )
    return True


orm.measure(corrector_names=corrector_names, callback=callback)
orm.save(parent_folder / Path("reduced_orm.json"))

ormdata = orm.get()
