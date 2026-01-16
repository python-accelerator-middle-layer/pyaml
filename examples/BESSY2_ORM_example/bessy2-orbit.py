import numpy as np
import time

from pyaml.accelerator import Accelerator
import matplotlib.pyplot as plt

sr = Accelerator.load("BESSY2Orbit.yaml")
orbit = sr.live.get_bpms("BPM").positions
hcorr = sr.live.get_magnets("HCorr")
vcorr = sr.live.get_magnets("VCorr")

# Mangle the orbit
std_kick = 1e-6
hcorr.strengths.set(std_kick * np.random.normal(size=len(hcorr)))
vcorr.strengths.set(std_kick * np.random.normal(size=len(vcorr)))
time.sleep(3)
positions_bc = orbit.get()

fig = plt.figure()
ax1 = fig.add_subplot(311)
ax2 = fig.add_subplot(312)
ax3 = fig.add_subplot(313)
ax1.plot(positions_bc[:, 0] * 1e-3, label="Orbit before correction")
ax2.plot(positions_bc[:, 1] * 1e-3, label="Orbit before correction")
#ax1.plot(positions_ac[:, 0] * 1e6, label="Orbit after correction")
#ax2.plot(positions_ac[:, 1] * 1e6, label="Orbit after correction")

ax3.plot(hcorr.strengths.get())
ax3.plot(vcorr.strengths.get())

ax1.set_ylabel("Horizontal pos. [μm]")
ax2.set_ylabel("Vertical pos. [μm]")
ax2.set_xlabel("BPM number")
ax3.set_ylabel("Strength (rad)")
ax3.set_xlabel("Steerer number")
fig.tight_layout()

plt.show()

