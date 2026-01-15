import numpy as np

from pyaml.accelerator import Accelerator

sr = Accelerator.load("BESSY2Orbit.yaml")
orbit = sr.live.get_bpms("BPM").positions.get()
names = sr.live.get_bpms("BPM").names()
for idx, n in enumerate(names):
    print(f"{n}:{orbit[idx]}")
print(sr.live.get_rf_plant("RF").frequency.get())
