import os

import numpy as np

from pyaml.accelerator import Accelerator
from pyaml.common.constants import ACTION_RESTORE
from pyaml.magnet.magnet import Magnet

# Get the directory of the current script
script_dir = os.path.dirname(__file__)

# Go up one level and then into 'data'
relative_path = os.path.join(script_dir, "..", "..", "tests", "config", "EBSTune.yaml")

# Normalize the path (resolves '..')
absolute_path = os.path.abspath(relative_path)

sr: Accelerator = Accelerator.load(absolute_path)

# switch design/live
SR = sr.design
# SR = sr.live
print(SR)

exit()
# Callback exectued after each magnet strenght setting
# during the tune response matrix measurement
def tune_callback(step: int, action: int, m: Magnet, dtune: np.array):
    if action == ACTION_RESTORE:
        # On action restore, the delta tune is passed as argument
        print(f"Tune response: #{step} {m.get_name()} {dtune}")
    return True

# Compute tune response matrix from lattice model (design)
sr.design.get_lattice().disable_6d()
tune_adjust_design = sr.design.tune
tune_adjust_design.response.measure(callback=tune_callback)
tune_adjust_design.response.save_json("tunemat.json")

# Correct tune on live
tune_adjust_live = SR.tune
tune_adjust_live.response.load_json("tunemat.json")
print('initial tune value')
print(tune_adjust_live.readback())
print('move tune to [0.17, 0.32] and wait 10s for 2 iterations')
tune_adjust_live.set([0.17, 0.32], iter=2, wait_time=10)
print('final measured tune value (expected [0.17, 0.32])')
print(tune_adjust_live.readback())
