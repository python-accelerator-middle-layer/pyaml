from pathlib import Path

import matplotlib.pyplot as plt

from pyaml.accelerator import Accelerator
from pyaml.tuning_tools.dispersion import ConfigModel as Disp_ConfigModel
from pyaml.tuning_tools.dispersion import Dispersion

parent_folder = Path(__file__).parent
config_path = parent_folder.parent.parent.joinpath(
    "tests", "config", "EBSOrbit.yaml"
).resolve()
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

fig = plt.figure()
ax = fig.add_subplot(111)
ax.plot(dispersion_data["frequency_response_x"])
plt.show()
