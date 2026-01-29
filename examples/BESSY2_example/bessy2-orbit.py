"""Orbit correction

This example shows how to run orbit correction using the simulator or the virtual accelerator.
If you want to test the virtual accelerator you need to start the container before running the script.

"""

import json
import time

import matplotlib.pyplot as plt
import numpy as np

from pyaml.accelerator import Accelerator
from pyaml.tuning_tools.orbit_response_matrix import ConfigModel as ORM_ConfigModel
from pyaml.tuning_tools.orbit_response_matrix import OrbitResponseMatrix

# ----- Load the configuration -----
# Remember to change the prefix for the live mode to the one matching your virtual accelerator before loading.

sr = Accelerator.load("BESSY2Orbit.yaml")

# ----- Measure the orbit response matrix -----
# If there is no existing orbit response matrix you need to measure it. This can be done on either the design or live mode.
# It is also possible to measure the ORM using the design mode and use it to correct the live mode.

# Choose which backend to use.
SR = sr.design
# SR = sr.live

# if the ORM is not present measure it
if sr.design.orbit.response_matrix is None:
    SR.orm.measure(set_wait_time=0.0 if SR == sr.design else 2.0)
    orm_data = SR.orm.get()

    # Save the data to json
    ORM_data = {
        "type": "pyaml.tuning_tools.response_matrix",
        "matrix": orm_data["matrix"],
        "input_names": orm_data["input_names"],
        "output_names": orm_data["output_names"],
        "inputs_plane": orm_data["inputs_plane"],
        "outputs_plane": orm_data["outputs_plane"],
    }
    json.dump(ORM_data, open("orm.json", "w"))

# ----- Load the response matrix -----
# The example does the correction for the live mode but it can also be done on the design mode.

# Load the ORM for the live mode
sr.live.orbit.load_response_matrix("orm.json")

# ----- Correct the orbit -----

# Get the devices
hcorr = sr.live.get_magnets("HCorr")
vcorr = sr.live.get_magnets("VCorr")
orbit = sr.live.get_bpms("BPM").positions

# Create an initial orbit with errors
std_kick = 10e-6
hcorr.strengths.set(std_kick * np.random.normal(size=len(hcorr)))
vcorr.strengths.set(std_kick * np.random.normal(size=len(vcorr)))
time.sleep(3)

orbit_initial = orbit.get()

# Correct the orbit
# If you are using the ORM measured on design to correct on live you need to set the gain
# since the unit for the BPMs are not the same for both modes yet.

sr.live.orbit.correct(gain=1e-9)
# sr.design.orbit.correct()
# sr.live.orbit.correct()

time.sleep(3)
orbit_after = orbit.get()

# ----- Plot the results -----
# Remember: if you change the example from live to design you need to change the unit for the orbit when plotting since not the same yet.
# If you are running in VS code you might need to switch the matplotlib backend for the plot to show.

fig = plt.figure()
ax1 = fig.add_subplot(311)
ax2 = fig.add_subplot(312)
ax3 = fig.add_subplot(313)
ax1.plot(orbit_initial[:, 0] * 1e-6, label="Orbit before correction")
ax2.plot(orbit_initial[:, 1] * 1e-6, label="Orbit before correction")
ax1.plot(orbit_after[:, 0] * 1e-6, label="Orbit after correction")
ax2.plot(orbit_after[:, 1] * 1e-6, label="Orbit after correction")

ax3.plot(hcorr.strengths.get() * 1e6, label="H Steerers")
ax3.plot(vcorr.strengths.get() * 1e6, label="V Steerers")

ax1.set_ylabel("Horizontal pos. [mm]")
ax2.set_ylabel("Vertical pos. [mm]")
ax2.set_xlabel("BPM number")
ax3.set_ylabel("Strength (urad)")
ax3.set_xlabel("Steerer number")
ax1.legend()
ax2.legend()
ax3.legend()
fig.tight_layout()

plt.show()
