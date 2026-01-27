import numpy as np

from pyaml.accelerator import Accelerator
from pyaml.common.constants import ACTION_MEASURE


def chroma_callback(step: int, action: int, rf: float, tune: np.array):
    if action == ACTION_MEASURE:
        print(f"Chromaticy measurement: #{step} RF={rf} Tune={tune}")
    return True


sr = Accelerator.load("BESSY2Chroma.yaml")
sr.design.get_lattice().disable_6d()
# Retreive MCF from the model
alphac = sr.design.get_lattice().get_mcf()
print(f"Moment compaction factor: {alphac}")
chromaticity_monitor = sr.live.get_chromaticity_monitor("KSI")
chromaticity_monitor.measure(do_plot=True, alphac=alphac, callback=chroma_callback)
ksi = chromaticity_monitor.chromaticity.get()
print(ksi)
