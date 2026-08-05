import numpy as np
import pytest

from pyaml.accelerator import Accelerator


def test_bba():
    sr = Accelerator.load("tests/config/EBSOrbit.yaml")
    SR = sr.design

    # Add a misalignement
    SR.get_bpm("BPM_C04-04").offset.set([20e-6, -15e-6])

    # BBA (standard bow tie, model independant)
    bba = SR.get_bba("BBA-BPM_C04-04")
    bba.measure()
    assert np.abs(bba.h_offset() - 20e-6) < 1e-6
    assert np.abs(bba.v_offset() + 15e-6) < 1e-6

    # BBA (model dependant method)
    bba = SR.get_bba("BBA2-BPM_C04-04")
    bba._cfg.minicyle_sleep_time = 0
    bba.measure()
    assert np.abs(bba.h_offset() - 20e-6) < 1e-6
    assert np.abs(bba.v_offset() + 15e-6) < 1e-6
    assert np.abs(bba.h_offset_error() - 3.425616879733572e-07) < 1e-10
    assert np.abs(bba.v_offset_error() - 2.593196843945284e-07) < 1e-10
