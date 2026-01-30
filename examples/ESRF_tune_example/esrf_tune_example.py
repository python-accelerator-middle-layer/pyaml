import os

import numpy as np

from pyaml.accelerator import Accelerator
from pyaml.common.constants import ACTION_RESTORE
from pyaml.magnet.magnet import Magnet

sr: Accelerator = Accelerator.load('./pyaml/tests/config/EBSTune.yaml')
sr.design.get_lattice().disable_6d()

# switch script from live to design
SR = sr.design # acts on simulations sr.live to act on real machine 


# Callback exectued after each magnet strenght setting
# during the tune response matrix measurement
def tune_callback(step: int, action: int, m: Magnet, dtune: np.array):
    if action == ACTION_RESTORE:
        # On action restore, the delta tune is passed as argument
        print(f"Tune response: #{step} {m.get_name()} {dtune}")
    return True


# Compute tune response matrix
tune_adjust_design = sr.design.get_tune_tuning("TUNE")
tune_adjust_design.response.measure(callback=tune_callback)
tune_adjust_design.response.save_json("tunemat.json")

# Correct tune on live or design
tune_adjust = SR.get_tune_tuning("TUNE")
tune_adjust.response.load_json("tunemat.json")
print(tune_adjust.readback())
tune_adjust.set([0.17, 0.32], iter=2, wait_time=10)
print(tune_adjust.readback())
