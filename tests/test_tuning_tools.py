from pyaml.accelerator import Accelerator
from pyaml.magnet.magnet import Magnet
from pyaml.common.constants import ACTION_RESTORE
from pyaml.configuration.factory import Factory

import numpy as np

def tune_callback(step:int,action:int,m:Magnet,dtune:np.array):
    if action==ACTION_RESTORE:
        # On action restore, the delta tune is passed as argument
        print(f"Tune response: #{step} {m.get_name()} {dtune}")
    return True

def test_tuning_tools():

    sr = Accelerator.load("tests/config/EBSTune.yaml",use_fast_loader=False)
    sr.design.get_lattice().disable_6d()
    tune_adjust = sr.design.get_tune_tuning("TUNE")
    tune_adjust.response.measure(callback=tune_callback)
    tune_adjust.response.save_json("tunemat.json")
    tune_adjust.response.load_json("tunemat.json")
    tune_adjust.set([0.17,0.32],iter=2)
    tune = tune_adjust.get()
    assert np.abs(tune[0]-0.17) < 1e-5
    assert np.abs(tune[1]-0.32) < 1e-5

    Factory.clear()
