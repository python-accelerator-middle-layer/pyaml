
from pyaml.pyaml import PyAML, pyaml
from pyaml.instrument import Instrument
from pyaml.configuration.factory import Factory
import numpy as np
import at
import pytest

@pytest.mark.parametrize("install_test_package", [{
    "name": "tango",
    "path": "tests/dummy_cs/tango"
}], indirect=True)
def test_bpm(install_test_package):

    ml:PyAML = pyaml("tests/config/bpms.yaml")
    sr:Instrument = ml.get('sr')
    sr.design.get_lattice().disable_6d()

    bpm = sr.design.get_bpm('BPM_C03-02')

    assert( True )

    Factory.clear()
