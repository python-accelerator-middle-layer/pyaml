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

my_corr_name = "SJ2A-C04-H"
my_corr = ebs.get_magnet(my_corr_name)


weights = np.linspace(0.01, 2, 100)
corr_settings = np.zeros_like(weights)
########################################################
for i, w in enumerate(weights):
    hcorr.strengths.set(h0)
    my_corr.strength.set(0)
    vcorr.strengths.set(v0)
    ebs.orbit.set_weight(my_corr_name, w)

    ebs.orbit.correct(reference=reference)
    corr_settings[i] = my_corr.strength.get()

fig = plt.figure()
ax1 = fig.add_subplot(111)
ax1.plot(weights, corr_settings * 1e6, ".")


ax1.set_ylabel("Corrector setting [μrad]")
ax1.set_xlabel("Corrector weight")
fig.tight_layout()

plt.show()
