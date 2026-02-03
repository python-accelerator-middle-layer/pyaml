import pytest

from pyaml.accelerator import Accelerator
from pyaml.configuration.factory import Factory


def test_simulator_tune_monitor():
    sr: Accelerator = Accelerator.load(
        "tests/config/tune_monitor.yaml", ignore_external=True
    )
    sr.design.get_lattice().disable_6d()
    tune_monitor = sr.design.get_betatron_tune_monitor("BETATRON_TUNE")
    assert tune_monitor.tune.get()[0] == sr.design.get_lattice().get_tune()[0]
    assert tune_monitor.tune.get()[1] == sr.design.get_lattice().get_tune()[1]

    Factory.clear()


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_controlsystem_tune_monitor(install_test_package):
    sr: Accelerator = Accelerator.load("tests/config/tune_monitor.yaml")
    tune_monitor = sr.live.get_betatron_tune_monitor("BETATRON_TUNE")
    assert tune_monitor.tune.get()[0] == 0.0
    assert tune_monitor.tune.get()[1] == 0.0

    Factory.clear()
