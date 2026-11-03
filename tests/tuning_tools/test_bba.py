import numpy as np

from pyaml.accelerator import Accelerator
from pyaml.common.constants import Action


def test_bba():
    sr = Accelerator.load("tests/config/EBSOrbit.yaml")
    SR = sr.design

    # Add a misalignement
    SR.diagnostic.bpm.get("BPM_C04-04").offset.set([20e-6, -15e-6])

    # for callback testing
    actions = []

    def callback(action, data):
        actions.append(action)
        return True

    # BBA (standard bow tie, model independant)
    bba = SR.tool.get("BBA-BPM_C04-04")
    bba.measure(callback=callback)
    assert np.abs(bba.h_offset() - 20e-6) < 1e-6
    assert np.abs(bba.v_offset() + 15e-6) < 1e-6

    # check callback actions:
    assert Action.BEFORE_BPM_READING in actions
    assert Action.MEASURE in actions
    assert Action.INIT in actions
    assert Action.RESTORE in actions

    # BBA (model dependant method)
    bba = SR.tool.get("BBA2-BPM_C04-04")
    bba.minicycle_sleep_time = 0
    bba.measure()
    assert np.abs(bba.h_offset() - 20e-6) < 1e-6
    assert np.abs(bba.v_offset() + 15e-6) < 1e-6
    assert np.abs(bba.h_offset_error() - 3.425616879733572e-07) < 1e-10
    assert np.abs(bba.v_offset_error() - 2.593196843945284e-07) < 1e-10


@pytest.mark.parametrize("bipolar", [False, True])
def test_bba_bipolar(bipolar):
    sr = Accelerator.load("tests/config/EBSOrbit.yaml")
    SR = sr.design
    SR.diagnostic.bpm.get("BPM_C04-04").offset.set([20e-6, -15e-6])

    bba = SR.tool.get("BBA-BPM_C04-04")
    assert bba.bipolar is False
    k1 = bba.quadrupole.strength.get()
    bba.measure(bipolar=bipolar)
    assert np.abs(bba.h_offset() - 20e-6) < 1e-6
    assert np.abs(bba.v_offset() + 15e-6) < 1e-6
    assert bba.quadrupole.strength.get() == pytest.approx(k1)
