"""Tune correction

This example shows how to run tune correction using the simulator
or the virtual accelerator.
If you want to test the virtual accelerator you need to start the
container before running the script.

"""

import time

import numpy as np

from pyaml.accelerator import Accelerator
from pyaml.common.constants import Action
from pyaml.magnet.magnet import Magnet

# ----- Load the configuration -----
# Remember to change the prefix for the live mode to the one matching
# your virtual accelerator before loading.

sr = Accelerator.load("BESSY2Tune.yaml")

# ----- Define a callback -----
# This callback is used to print output during the tune response measurement.


def tune_callback(action: int, cb_data: dict):
    if action == Action.MEASURE:
        # On action measure, the measured dq / dk is passed as argument
        print(f"Tune response: #{cb_data['step']} {cb_data['magnet']} {cb_data['tune']}")
    return True


# ----- Measure the tune response matrix-----
# You can measure the tune response matrix on either the design or live mode.
# At the moment they don't give the same result.
# This will be fixed later by switching to using SerializedMagnet.

# Choose which backend to use.
SR = sr.design

# if the TRM is not present measure it
if sr.design.tune.response_matrix is None:
    SR.trm.measure(sleep_between_step=0.0 if SR == sr.design else 2.0, callback=tune_callback)
    SR.trm.save("trm.json")
    # Load it on live
    sr.live.tune.load("trm.json")

# ----- Correct the tune -----

print("\nRun tune correction:")

initial_tunes = np.array2string(sr.live.tune.readback(), precision=6, floatmode="fixed")
print(f"Initial tunes: {initial_tunes}")

sr.live.tune.set([0.83, 0.84], iter=2, wait_time=3)
time.sleep(3)

final_tunes = np.array2string(sr.live.tune.readback(), precision=6, floatmode="fixed")
print(f"Final tunes: {final_tunes}")
