import numpy as np

from pyaml.accelerator import Accelerator
from pyaml.common.constants import Action


def tune_callback(action: Action, data: dict):
    source = data["source"]
    if action == Action.APPLY:
        # ACTION_APPLY
        step = data["step"]
        m = data["magnet"]
        print(f"{action} {source}: #{step} {m.get_name()} = {m.strength.get()}")
    elif action == Action.MEASURE:
        # On ACTION_MEASURE, the tune is passed as argument
        step = data["step"]
        avg_step = data["avg_step"]
        m = data["magnet"]
        tune = data["tune"]
        print(f"{action} {source}: #{step} {avg_step} {m.get_name()} q={tune}")
    elif action == Action.RESTORE:
        # On ACTION_RESTORE, the delta tune is passed as argument
        step = data["step"]
        m = data["magnet"]
        dtune = data["dtune"]
        print(f"{action} {source}: #{step} {m.get_name()} dq/dk={dtune}")
    return True


def test_tuning_tools():
    sr = Accelerator.load("tests/config/EBSTune.yaml", use_fast_loader=False)
    sr.design.get_lattice().disable_6d()
    sr.design.trm.measure(callback=tune_callback)
    sr.design.trm.save("tunemat.json")
    sr.design.tune.load("tunemat.json")
    sr.design.tune.set([0.17, 0.32], iter=2)
    tune = sr.design.tune.readback()
    assert np.abs(tune[0] - 0.17) < 1e-5
    assert np.abs(tune[1] - 0.32) < 1e-5


def test_tune_add():
    sr = Accelerator.load("tests/config/EBSTune.yaml", use_fast_loader=False)
    sr.design.get_lattice().disable_6d()
    sr.design.tune.load("tunemat.json")
    tune_initial = sr.design.tune.readback()
    dtune = np.array([0.01, -0.01])
    sr.design.tune.add(dtune)
    tune = sr.design.tune.readback()
    np.testing.assert_allclose(tune - tune_initial, dtune, atol=1e-5)
