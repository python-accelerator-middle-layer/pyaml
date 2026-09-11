import numpy as np
import pytest


def test_simulator_tune_monitor(
    accelerator_from_fragments,
    tune_monitor_configuration_fragments,
):
    sr = accelerator_from_fragments(
        *tune_monitor_configuration_fragments,
        ignore_external=True,
    )
    sr.design.get_lattice().disable_6d()
    tune_monitor = sr.design.get_betatron_tune_monitor("BETATRON_TUNE")
    assert tune_monitor.tune.get()[0] == sr.design.get_lattice().get_tune()[0]
    assert tune_monitor.tune.get()[1] == sr.design.get_lattice().get_tune()[1]
    assert np.abs(tune_monitor.frequency.get()[0] - 56834.22592393) < 1e-6
    assert np.abs(tune_monitor.frequency.get()[1] - 120772.67004602) < 1e-6


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_controlsystem_tune_monitor(
    install_test_package,
    accelerator_from_fragments,
    tune_monitor_configuration_fragments,
):
    sr = accelerator_from_fragments(
        *tune_monitor_configuration_fragments,
    )
    tune_monitor = sr.live.get_betatron_tune_monitor("BETATRON_TUNE")
    assert tune_monitor.tune.get()[0] == 0.0
    assert tune_monitor.tune.get()[1] == 0.0
