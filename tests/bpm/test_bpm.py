import numpy as np
import pytest

from pyaml.accelerator import Accelerator


def test_simulator_bpm_tilt():
    sr: Accelerator = Accelerator.load("tests/config/bpms.yaml", ignore_external=True)
    sr.design.get_lattice().disable_6d()
    sr.design.get_magnet("SH1A-C01-H").strength.set(10e-6)  # Add orbit
    sr.design.get_magnet("SH1A-C01-V").strength.set(10e-6)  # Add orbit
    bpm = sr.design.get_bpm("BPM_C01-01")
    assert np.allclose(bpm.positions.get(), np.array([5.90809968e-05, 2.24832853e-05]))
    assert bpm.tilt.get() == 0
    alpha = np.pi / 3
    bpm.tilt.set(alpha)
    assert bpm.tilt.get() == alpha

    new_x = 5.908792e-05 * np.cos(alpha) - 2.24832853e-05 * np.sin(alpha)
    new_y = 5.908792e-05 * np.sin(alpha) + 2.24832853e-05 * np.cos(alpha)
    assert np.allclose(bpm.positions.get(), np.array([new_x, new_y]))

    alpha = np.pi / 2
    bpm.tilt.set(alpha)
    new_x = 5.908792e-05 * np.cos(alpha) - 2.24832853e-05 * np.sin(alpha)
    new_y = 5.908792e-05 * np.sin(alpha) + 2.24832853e-05 * np.cos(alpha)
    assert np.allclose(bpm.positions.get(), np.array([new_x, new_y]))


def test_simulator_bpm_offset():
    sr: Accelerator = Accelerator.load("tests/config/bpms.yaml", ignore_external=True)
    sr.design.get_lattice().disable_6d()
    bpm = sr.design.get_bpm("BPM_C01-01")

    assert bpm.offset.get()[0] == 0
    assert bpm.offset.get()[1] == 0
    bpm.offset.set(np.array([0.1, 0.2]))
    assert bpm.offset.get()[0] == 0.1
    assert bpm.offset.get()[1] == 0.2
    assert np.allclose(bpm.positions.get(), np.array([0.1, 0.2]))


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_simulator_bpm_position(install_test_package):
    sr: Accelerator = Accelerator.load("tests/config/bpms.yaml")
    sr.design.get_lattice().disable_6d()
    bpm = sr.design.get_bpm("BPM_C01-01")
    bpm_simple = sr.live.get_bpm("BPM_C01-02")

    assert np.allclose(bpm.positions.get(), np.array([0.0, 0.0]))
    assert np.allclose(bpm_simple.positions.get(), np.array([0.0, 0.0]))


def test_simulator_bpm_position_with_bad_corrector_strength():
    sr: Accelerator = Accelerator.load("tests/config/bpms.yaml", ignore_external=True)
    sr.design.get_lattice().disable_6d()
    bpm1 = sr.design.get_bpm("BPM_C01-01")
    bpm_simple = sr.design.get_bpm("BPM_C01-02")
    bpm3 = sr.design.get_bpm("BPM_C01-03")

    sr.design.get_magnet("SH1A-C01-H").strength.set(-1e-6)
    sr.design.get_magnet("SH1A-C01-V").strength.set(-1e-6)
    for bpm in [bpm1, bpm_simple, bpm3]:
        assert bpm.positions.get()[0] != 0.0
        assert bpm.positions.get()[1] != 0.0
