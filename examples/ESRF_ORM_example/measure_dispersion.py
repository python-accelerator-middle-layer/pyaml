from pathlib import Path

import matplotlib.pyplot as plt

from pyaml.accelerator import Accelerator
from pyaml.common.constants import Action

parent_folder = Path(__file__).parent
config_path = parent_folder.parent.parent.joinpath("tests", "config", "EBSOrbit.yaml").resolve()
sr = Accelerator.load(config_path)
ebs = sr.design


def callback(action: int, callback_data) -> bool:
    if action == Action.APPLY:
        print("Changing RF frequency")
    elif action == Action.MEASURE:
        print("Reading orbit.")
    elif action == Action.RESTORE:
        print("Restoring RF frequency.")
    return True


ebs.dispersion.measure(callback=callback)
dispersion_data = ebs.dispersion.get()

fig = plt.figure()
ax = fig.add_subplot(111)
ax.plot(dispersion_data["frequency_response_x"])
plt.show()
