import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from pyaml.accelerator import Accelerator

parent_folder = Path(__file__).parent
pyaml_folder = parent_folder.parent.parent
config_path = pyaml_folder.joinpath("tests/config/EBSOrbit.yaml").resolve()
sr = Accelerator.load(config_path)
# ebs = sr.live
ebs = sr.design

## get reference
ref_h, ref_v = ebs.get_bpms("BPM").positions.get().T
reference = np.concatenate((ref_h, ref_v))
########################################################

hcorr = ebs.get_magnets("HCorr")
vcorr = ebs.get_magnets("VCorr")
bpms = ebs.get_bpms("BPM")

if ebs == sr.design:
    ## generate some orbit
    std_kick = 1e-6

    np.random.seed(1)
    # mangle orbit
    hcorr.strengths.set(hcorr.strengths.get() + std_kick * np.random.normal(size=len(hcorr)))
    vcorr.strengths.set(vcorr.strengths.get() + std_kick * np.random.normal(size=len(vcorr)))

h0 = hcorr.strengths.get()
v0 = vcorr.strengths.get()

positions_bc = bpms.positions.get()
std_bc = np.std(positions_bc, axis=0)
print(f"R.m.s. orbit before correction H: {1e6 * std_bc[0]: .1f} µm, V: {1e6 * std_bc[1]: .1f} µm.")
########################################################

ebs.orbit.set_virtual_weight(1000)
## Correct the orbit
ebs.orbit.correct(reference=None, rf=True)
# ebs.orbit.correct(plane="H")
# ebs.orbit.correct(plane="V")
########################################################

time.sleep(5)

## inspect orbit correction
positions_ac = bpms.positions.get()
std_ac = np.std(positions_ac, axis=0)
print(f"R.m.s. orbit after correction H: {1e6 * std_ac[0]: .1f} µm, V: {1e6 * std_ac[1]: .1f} µm,")

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

print(f"Sum of h. corr. trims: {np.sum(hcorr.strengths.get() - h0)}")
print(f"Sum of v. corr. trims: {np.sum(vcorr.strengths.get() - v0)}")
plt.show()
