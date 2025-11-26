import json
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from pyaml.external.pySC.pySC.apps import orbit_correction
from pyaml.external.pySC.pySC.tuning.response_matrix import ResponseMatrix

from pyaml.accelerator import Accelerator
from pyaml.external.pySC import pySC
from pyaml.external.pySC_interface import pySCInterface

logging.getLogger("pyaml.external.pySC").setLevel(logging.WARNING)

parent_folder = Path(__file__).parent
pyaml_folder = parent_folder.parent.parent
config_path = pyaml_folder.joinpath("tests/config/EBSOrbit.yaml").resolve()
sr = Accelerator.load(config_path)
ebs = sr.design

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

response_matrix = ResponseMatrix.from_json(parent_folder / Path("ideal_orm.json"))
interface = pySCInterface(element_holder=ebs)
trims = orbit_correction(
    interface=interface,
    response_matrix=response_matrix,
    method="svd_cutoff",
    parameter=1e-3,
    zerosum=True,
    apply=True,
)

positions_ac = bpms.positions.get()
std_ac = np.std(positions_ac, axis=0)
print(
    "R.m.s. orbit after correction H: "
    f"{1e6 * std_ac[0]: .1f} µm, V: {1e6 * std_ac[1]: .1f} µm,"
)


fig = plt.figure()
ax1 = fig.add_subplot(211)
ax2 = fig.add_subplot(212)
ax1.plot(positions_bc[:, 0] * 1e6, label="Orbit before correction")
ax2.plot(positions_bc[:, 1] * 1e6, label="Orbit before correction")
ax1.plot(positions_ac[:, 0] * 1e6, label="Orbit after correction")
ax2.plot(positions_ac[:, 1] * 1e6, label="Orbit after correction")

ax1.set_ylabel("Horizontal pos. [μm]")
ax2.set_ylabel("Vertical pos. [μm]")
ax2.set_xlabel("BPM number")
plt.show()
