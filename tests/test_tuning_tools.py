import numpy as np

from pyaml.accelerator import Accelerator
from pyaml.common.constants import ACTION_RESTORE
from pyaml.magnet.magnet import Magnet


def tune_callback(step: int, action: int, m: Magnet, dtune: np.array):
    if action == ACTION_RESTORE:
        # On action restore, the delta tune is passed as argument
        print(f"Tune response: #{step} {m.get_name()} {dtune}")
    return True


def test_tuning_tools():
    sr = Accelerator.load("tests/config/EBSTune.yaml", use_fast_loader=False)
    sr.design.get_lattice().disable_6d()
    sr.design.tune.response.measure(callback=tune_callback)
    sr.design.tune.response.save_json("tunemat.json")
    sr.design.tune.response.load_json("tunemat.json")
    sr.design.tune.set([0.17, 0.32], iter=2)
    tune = sr.design.tune.readback()
    assert np.abs(tune[0] - 0.17) < 1e-5
    assert np.abs(tune[1] - 0.32) < 1e-5


def test_tune_step():
    sr = Accelerator.load("tests/config/EBSTune.yaml", use_fast_loader=False)
    sr.design.get_lattice().disable_6d()
    sr.design.tune.response.measure(callback=tune_callback)
    tune_initial = sr.design.tune.readback()
    dtune = np.array([0.01, -0.01])
    sr.design.tune.step(dtune)
    tune = sr.design.tune.readback()
    np.testing.assert_allclose(tune - tune_initial, dtune, atol=1e-5)
