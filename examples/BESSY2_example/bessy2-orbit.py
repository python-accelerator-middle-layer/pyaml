import json
import time

import matplotlib.pyplot as plt
import numpy as np

from pyaml.accelerator import Accelerator
from pyaml.tuning_tools.orbit_response_matrix import ConfigModel as ORM_ConfigModel
from pyaml.tuning_tools.orbit_response_matrix import OrbitResponseMatrix

sr = Accelerator.load("BESSY2Orbit.yaml")
orbit = sr.live.get_bpms("BPM").positions
hcorr = sr.live.get_magnets("HCorr")
vcorr = sr.live.get_magnets("VCorr")
nbBPM = len(sr.live.get_bpms("BPM"))

if sr.design.orbit.response_matrix is None:
    # Measure ORM on design
    orm = OrbitResponseMatrix(
        cfg=ORM_ConfigModel(
            bpm_array_name="BPM",
            hcorr_array_name="HCorr",
            vcorr_array_name="VCorr",
            corrector_delta=1e-6,
        ),
        element_holder=sr.design,
    )
    orm.measure()
    orm_data = orm.get()
    ideal_ORM_data = {
        "type": "pyaml.tuning_tools.response_matrix",
        "matrix": orm_data["matrix"],
        "input_names": orm_data["input_names"],
        "output_names": orm_data["output_names"],
        "rf_response": list(np.zeros(nbBPM).tolist()),
    }
    json.dump(ideal_ORM_data, open("ideal_orm.json", "w"))
    sr.live.orbit.load_response_matrix("ideal_orm.json")

# Mangle the orbit
std_kick = 1e-6
hcorr.strengths.set(std_kick * np.random.normal(size=len(hcorr)))
vcorr.strengths.set(std_kick * np.random.normal(size=len(vcorr)))
# sr.live.get_magnet("VS2M2D1R").strength.set(std_kick)
# sr.design.get_magnet("VS2M2D1R").strength.set(std_kick)
time.sleep(3)

# positions_bc = sr.live.get_bpms("BPM").positions.get()
# positions_ac = sr.design.get_bpms("BPM").positions.get()


positions_bc = orbit.get()
# Correct
sr.live.orbit.correct()
time.sleep(3)
positions_ac = orbit.get()

# Plot
fig = plt.figure()
ax1 = fig.add_subplot(311)
ax2 = fig.add_subplot(312)
ax3 = fig.add_subplot(313)
ax1.plot(positions_bc[:, 0] * 1e6, label="Orbit before correction")
ax2.plot(positions_bc[:, 1] * 1e6, label="Orbit before correction")
ax1.plot(positions_ac[:, 0] * 1e6, label="Orbit after correction")
ax2.plot(positions_ac[:, 1] * 1e6, label="Orbit after correction")

ax3.plot(hcorr.strengths.get(), label="H Steerers")
ax3.plot(vcorr.strengths.get(), label="V Steerers")

ax1.set_ylabel("Horizontal pos. [μm]")
ax2.set_ylabel("Vertical pos. [μm]")
ax2.set_xlabel("BPM number")
ax3.set_ylabel("Strength (rad)")
ax3.set_xlabel("Steerer number")
ax1.legend()
ax2.legend()
ax3.legend()
fig.tight_layout()

plt.show()
