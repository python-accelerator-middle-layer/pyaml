import numpy as np
import pytest

from pyaml.accelerator import Accelerator


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_controlsystem_bpm_tilt(install_test_package):
    sr: Accelerator = Accelerator.load("tests/config/bpms.yaml")
    bpm = sr.live.get_bpm("BPM_C01-01")
    print(bpm.tilt.get())

    assert bpm.tilt.get() == 0
    bpm.tilt.set(0.01)
    assert bpm.tilt.get() == 0.01


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_controlsystem_bpm_offset(install_test_package):
    sr: Accelerator = Accelerator.load("tests/config/bpms.yaml")
    bpm = sr.live.get_bpm("BPM_C01-01")

    assert bpm.offset.get()[0] == 0
    assert bpm.offset.get()[1] == 0
    bpm.offset.set(np.array([0.1, 0.2]))
    assert bpm.offset.get()[0] == 0.1
    assert bpm.offset.get()[1] == 0.2
    assert np.allclose(bpm.positions.get(), np.array([0.0, 0.0]))


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_controlsystem_bpm_position(install_test_package):
    sr: Accelerator = Accelerator.load("tests/config/bpms.yaml")
    bpm = sr.live.get_bpm("BPM_C01-01")
    bpm_simple = sr.live.get_bpm("BPM_C01-02")

    assert np.allclose(bpm.positions.get(), np.array([0.0, 0.0]))
    assert np.allclose(bpm_simple.positions.get(), np.array([0.0, 0.0]))


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_controlsystem_bpm_position_indexed(install_test_package):
    sr: Accelerator = Accelerator.load("tests/config/bpms.yaml")
    bpm = sr.live.get_bpm("BPM_C01-04")

    assert np.allclose(bpm.positions.get(), np.array([0.0, 1.0]))
