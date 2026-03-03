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

## get reference
ref_h, ref_v = ebs.get_bpms("BPM").positions.get().T
reference = np.concatenate((ref_h, ref_v))
########################################################


## generate some orbit
std_kick = 1e-6
hcorr = ebs.get_magnets("HCorr")
vcorr = ebs.get_magnets("VCorr")
bpms = ebs.get_bpms("BPM")

np.random.seed(1)
# mangle orbit
h0 = hcorr.strengths.get() + std_kick * np.random.normal(size=len(hcorr))
v0 = vcorr.strengths.get() + std_kick * np.random.normal(size=len(vcorr))

my_bpm_name = "BPM_C04-05"
my_bpm = ebs.get_bpm(my_bpm_name)

weights = np.linspace(0.01, 10, 40)
bpm_reading = np.zeros_like(weights)
ref_bpm_reading = my_bpm.positions.get()[0]
########################################################
for i, w in enumerate(weights):
    hcorr.strengths.set(h0)
    vcorr.strengths.set(v0)
    ebs.orbit.response_matrix.set_weight(my_bpm_name, w, plane="H")

    ebs.orbit.correct(singular_values_H=40, singular_values_V=40)
    ebs.orbit.correct(singular_values_H=40, singular_values_V=40)
    ebs.orbit.correct(singular_values_H=40, singular_values_V=40)
    bpm_reading[i] = my_bpm.positions.get()[0]

fig = plt.figure()
ax1 = fig.add_subplot(111)
ax1.plot(weights, bpm_reading * 1e6, ".")


ax1.set_ylabel("BPM reading [μm]")
ax1.set_xlabel("BPM weight")
fig.tight_layout()

plt.show()
