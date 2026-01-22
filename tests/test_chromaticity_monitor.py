import numpy as np
import pytest

from pyaml.accelerator import Accelerator
from pyaml.configuration.factory import Factory


def test_simulator_chromaticity_monitor():
    sr: Accelerator = Accelerator.load(
        "tests/config/EBS_chromaticity.yaml", ignore_external=True
    )
    sr.design.get_lattice().disable_6d()
    chromaticity_monitor = sr.design.get_chromaticity_monitor("KSI")
    assert (
        chromaticity_monitor.chromaticity.get()[0]
        == sr.design.get_lattice().get_chrom()[0]
    )
    assert (
        chromaticity_monitor.chromaticity.get()[1]
        == sr.design.get_lattice().get_chrom()[1]
    )

    Factory.clear()


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_controlsystem_chromaticity_monitor(install_test_package):
    sr: Accelerator = Accelerator.load("tests/config/EBS_chromaticity.yaml")
    chromaticity_monitor = sr.live.get_chromaticity_monitor("KSI")
    assert np.isnan(chromaticity_monitor.chromaticity.get()[0])
    assert np.isnan(chromaticity_monitor.chromaticity.get()[1])
    chromaticity_monitor.chromaticity_measurement(
        do_plot=False,
        alphac=1e-4,
        Sleep_between_meas=0,
        Sleep_between_RFvar=0,
        E_delta=1,
        Max_E_delta=1,
    )
    ksi = np.abs(chromaticity_monitor.chromaticity.get())
    assert abs(ksi[0]) < 1e-17
    assert abs(ksi[1]) < 1e-17

    Factory.clear()
