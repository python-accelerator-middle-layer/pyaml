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
    chromaticity_monitor = sr.design.get_chromaticity_monitor("CHROMATICITY_MONITOR")
    chromaticity_monitor.measure(
        alphac=mcf, fit_dispersion=True, sleep_between_meas=0, sleep_between_step=0, callback=callback
    )
    chroma = chromaticity_monitor.chromaticity.get()
    assert np.abs(chroma[0] - chromaAT[0]) < 1e-2
    assert np.abs(chroma[1] - chromaAT[1]) < 1e-2

    dispx = chromaticity_monitor.dispersion.get()[0, :]
    assert np.abs(dispx[0] + 0.00157552) < 1e-8
    assert np.abs(dispx[1] - 0.08024241) < 1e-8
    assert np.abs(dispx[2] - 0.07345349) < 1e-8
    assert np.abs(dispx[3] - 0.01317651) < 1e-8
    assert np.abs(dispx[4] - 0.01488452) < 1e-8
    assert np.abs(dispx[5] - 0.01489548) < 1e-8
    assert np.abs(dispx[6] - 0.0131858) < 1e-8
    assert np.abs(dispx[7] - 0.07340748) < 1e-8
    assert np.abs(dispx[8] - 0.08038594) < 1e-8
    assert np.abs(dispx[9] - 0.00146621) < 1e-8
    dispy = chromaticity_monitor.dispersion.get()[1, :]
    assert abs(np.mean(dispy)) < 1e-10


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_controlsystem_chromaticity_monitor(install_test_package):
    sr: Accelerator = Accelerator.load("tests/config/EBS_chromaticity.yaml")
    chromaticity_monitor = sr.live.get_chromaticity_monitor("CHROMATICITY_MONITOR")
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
