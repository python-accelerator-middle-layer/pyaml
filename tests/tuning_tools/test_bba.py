import numpy as np
import pytest

from pyaml.accelerator import Accelerator


def callback(action: int, data: dict):
    print(f"action:{action}, data:{data}")
    return True


def test_simulator_chromaticity_monitor():
    sr = Accelerator.load("tests/config/EBSOrbit.yaml")
    SR = sr.design
    bba = SR.get_bba("BBA-BPM_C04-03")

    # Add a misalignement
    SR.get_bpm("BPM_C04-03").offset.set([20e-6, -15e-6])
    # Measure offsets
    bba.measure()
    assert np.abs(bba.h_offset() - 20e-6) < 2e-6
    assert np.abs(bba.v_offset() + 15e-6) < 2e-6
