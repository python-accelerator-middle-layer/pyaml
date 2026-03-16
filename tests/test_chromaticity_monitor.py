import numpy as np
import pytest

from pyaml.accelerator import Accelerator


def callback(action: int, data: dict):
    print(f"action:{action}, data:{data}")
    return True


def test_simulator_chromaticity_monitor():
    sr: Accelerator = Accelerator.load("tests/config/EBS_chromaticity.yaml", ignore_external=True)
    sr.design.get_lattice().disable_6d()
    mcf = sr.design.get_lattice().get_mcf()
    sr.design.get_lattice().enable_6d()
    chromaAT = sr.design.get_lattice().get_chrom()[:-1]
    chromaticity_monitor = sr.design.chromaticity
    chromaticity_monitor.measure(alphac=mcf, sleep_between_meas=0, sleep_between_step=0, callback=callback)
    chroma = chromaticity_monitor.chromaticity.get()
    assert np.abs(chroma[0] - chromaAT[0]) < 1e-2
    assert np.abs(chroma[1] - chromaAT[1]) < 1e-2


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_controlsystem_chromaticity_monitor(install_test_package):
    sr: Accelerator = Accelerator.load("tests/config/EBS_chromaticity.yaml")
    chromaticity_monitor = sr.live.chromaticity
    assert chromaticity_monitor.chromaticity.get() is None
    chromaticity_monitor.measure(
        do_plot=False,
        alphac=1e-4,
        sleep_between_meas=0,
        sleep_between_step=0,
        e_delta=1,
        max_e_delta=1,
    )
    ksi = np.abs(chromaticity_monitor.chromaticity.get())
    assert abs(ksi[0]) < 1e-17
    assert abs(ksi[1]) < 1e-17
