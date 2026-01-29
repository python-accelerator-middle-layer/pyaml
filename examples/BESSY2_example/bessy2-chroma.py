"""Chromaticity measurement

This example shows how to run chromaticity measurement using the simulator
or the virtual accelerator.
If you want to test the virtual accelerator you need to start the
container before running the script.

"""

import numpy as np

from pyaml.accelerator import Accelerator
from pyaml.common.constants import ACTION_MEASURE

# ----- Load the configuration -----
# Remember to change the prefix for the live mode to the one matching
# your virtual accelerator before loading.

sr = Accelerator.load("BESSY2Chroma.yaml")

# ----- Define a callback -----
# This callback is used to print output during the chromaticity measurement.


def chroma_callback(step: int, action: int, rf: float, tune: np.array):
    if action == ACTION_MEASURE:
        print(f"Chromaticy measurement: #{step} RF={rf} Tune={tune}")
    return True


# ----- Get the momentum compaction factor-----
# To get the momentum compaction from the model you need to first turn 6D off.

sr.design.get_lattice().disable_6d()
alphac = sr.design.get_lattice().get_mcf()
sr.design.get_lattice().enable_6d()
print(f"Moment compaction factor: {alphac}")

# ----- Measure the chromaticity-----
# The measurement routing will also show a plot.

chromaticity_monitor = sr.live.get_chromaticity_monitor("KSI")
chromaticity_monitor.measure(do_plot=True, alphac=alphac, callback=chroma_callback)
ksi = chromaticity_monitor.chromaticity.get()
print(ksi)
