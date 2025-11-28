from pathlib import Path

import numpy as np

from pyaml.accelerator import Accelerator
from pyaml.external.pySC_interface import pySCInterface

config_path = (
    Path(__file__)
    .parent.parent.parent.joinpath("tests", "config", "EBSOrbit.yaml")
    .resolve()
)
sr = Accelerator.load(config_path)

live_h = sr.live.get_bpms("BPM").h.get()  # ok
design_h = sr.design.get_bpms("BPM").h.get()  # ok

interface = pySCInterface(element_holder=sr.design)

orbit_x, orbit_y = interface.get_orbit()

one_hcorr = interface.hcorr_names[10]

sp0 = interface.get(one_hcorr)
interface.set(one_hcorr, sp0 + 10e-6)

hcorr_setpoints = interface.get_many(interface.hcorr_names)
interface.set_many(hcorr_setpoints)

orbit_x2, orbit_y2 = interface.get_orbit()

print(np.std(orbit_x2 - orbit_x))
