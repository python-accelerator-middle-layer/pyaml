import json
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from pyaml.accelerator import Accelerator
from pyaml.tuning_tools.orbit import ConfigModel as Orbit_ConfigModel
from pyaml.tuning_tools.orbit import Orbit

parent_folder = Path(__file__).parent
pyaml_folder = parent_folder.parent.parent
config_path = pyaml_folder.joinpath("tests/config/EBSOrbit.yaml").resolve()
sr = Accelerator.load(config_path)
ebs = sr.design

orbit = Orbit(
    element_holder=ebs,
    cfg=Orbit_ConfigModel(
        bpm_array_name="BPM",
        hcorr_array_name="HCorr",
        vcorr_array_name="VCorr",
        singular_values=162,
        response_matrix_file=str(
            pyaml_folder.joinpath("examples/ESRF_ORM_example/ideal_orm.json").resolve()
        ),
    ),
)

## get reference
ref_h, ref_v = orbit.element_holder.get_bpms("BPM").positions.get().T
reference = np.concat((ref_h, ref_v))
########################################################


## generate some orbit
std_kick = 1e-6
hcorr = ebs.get_magnets("HCorr")
vcorr = ebs.get_magnets("VCorr")
bpms = ebs.get_bpms("BPM")

# mangle orbit
hcorr.strengths.set(
    hcorr.strengths.get() + std_kick * np.random.normal(size=len(hcorr))
)
vcorr.strengths.set(
    vcorr.strengths.get() + std_kick * np.random.normal(size=len(vcorr))
)

positions_bc = bpms.positions.get()
std_bc = np.std(positions_bc, axis=0)
print(
    "R.m.s. orbit before correction "
    f"H: {1e6 * std_bc[0]: .1f} µm, V: {1e6 * std_bc[1]: .1f} µm."
)
########################################################

## Correct the orbit
orbit.correct(reference=reference)
# orbit.correct(plane="H")
# orbit.correct(plane="V")
########################################################

## inspect orbit correction
positions_ac = bpms.positions.get()
std_ac = np.std(positions_ac, axis=0)
print(
    "R.m.s. orbit after correction H: "
    f"{1e6 * std_ac[0]: .1f} µm, V: {1e6 * std_ac[1]: .1f} µm,"
)

fig = plt.figure()
ax1 = fig.add_subplot(311)
ax2 = fig.add_subplot(312)
ax3 = fig.add_subplot(313)
ax1.plot(positions_bc[:, 0] * 1e6, label="Orbit before correction")
ax2.plot(positions_bc[:, 1] * 1e6, label="Orbit before correction")
ax1.plot(positions_ac[:, 0] * 1e6, label="Orbit after correction")
ax2.plot(positions_ac[:, 1] * 1e6, label="Orbit after correction")

ax3.plot(hcorr.strengths.get())
ax3.plot(vcorr.strengths.get())

ax1.set_ylabel("Horizontal pos. [μm]")
ax2.set_ylabel("Vertical pos. [μm]")
ax2.set_xlabel("BPM number")
ax3.set_ylabel("Strength (rad)")
ax3.set_xlabel("Steerer number")
fig.tight_layout()

plt.show()
