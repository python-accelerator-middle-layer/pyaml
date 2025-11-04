
from pyaml.pyaml import PyAML, pyaml
from pyaml.instrument import Instrument
from pyaml.configuration.factory import Factory
from pyaml.lattice.abstract_impl import RBetatronTuneArray
import numpy as np
import pytest

@pytest.mark.parametrize("install_test_package", [{
    "name": "tango-pyaml",
    "path": "tests/dummy_cs/tango-pyaml"
}], indirect=True)
def test_simulator_tune_monitor(install_test_package):

    ml:PyAML = pyaml("tests/config/tune_monitor.yaml")
    sr:Instrument = ml.get('sr')
    sr.design.get_lattice().disable_6d()
    tune_monitor = sr.design.get_betatron_tune_monitor("BETATRON_TUNE")
    assert tune_monitor.tune.get()[0] == sr.design.get_lattice().get_tune()[0]
    assert tune_monitor.tune.get()[1] == sr.design.get_lattice().get_tune()[1]

    Factory.clear()

@pytest.mark.parametrize("install_test_package", [{
    "name": "tango-pyaml",
    "path": "tests/dummy_cs/tango-pyaml"
}], indirect=True)
def test_constrolsystem_tune_monitor(install_test_package):

    ml:PyAML = pyaml("tests/config/tune_monitor.yaml")
    sr:Instrument = ml.get('sr')
    tune_monitor = sr.live.get_betatron_tune_monitor("BETATRON_TUNE")
    assert tune_monitor.tune.get()[0] == 0.0
    assert tune_monitor.tune.get()[1] == 0.0

    Factory.clear()

