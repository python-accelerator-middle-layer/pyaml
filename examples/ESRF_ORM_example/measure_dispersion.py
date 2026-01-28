from pathlib import Path

import matplotlib.pyplot as plt

from pyaml.accelerator import Accelerator
from pyaml.common.constants import ACTION_APPLY, ACTION_MEASURE, ACTION_RESTORE
from pyaml.tuning_tools.dispersion import ConfigModel as Disp_ConfigModel
from pyaml.tuning_tools.dispersion import Dispersion

parent_folder = Path(__file__).parent
config_path = parent_folder.parent.parent.joinpath(
    "tests", "config", "EBSOrbit.yaml"
).resolve()
sr = Accelerator.load(config_path)
ebs = sr.design


def callback(action: int, callback_data) -> bool:
    if action == ACTION_APPLY:
        print("Changing RF frequency.")
    elif action == ACTION_MEASURE:
        print("Reading orbit.")
    elif action == ACTION_RESTORE:
        print("Restoring RF frequency.")
    return True


ebs.dispersion.measure(callback=callback)
dispersion_data = ebs.dispersion.get()

fig = plt.figure()
ax = fig.add_subplot(111)
ax.plot(dispersion_data["frequency_response_x"])
plt.show()
