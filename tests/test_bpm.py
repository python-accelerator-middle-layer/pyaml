
from pyaml.pyaml import PyAML, pyaml
from pyaml.instrument import Instrument
from pyaml.configuration.factory import Factory
import numpy as np
import pytest

@pytest.mark.parametrize("install_test_package", [{
    "name": "tango",
    "path": "tests/dummy_cs/tango"
}], indirect=True)
def test_simulator_bpm_tilt(install_test_package):

    ml:PyAML = pyaml("tests/config/bpms.yaml")
    sr:Instrument = ml.get('sr')
    sr.design.get_lattice().disable_6d()
    bpm = sr.design.get_bpm('BPM_C01-01')
    assert bpm.tilt.get() == 0
    bpm.tilt.set(0.01)
    assert bpm.tilt.get() == 0.01

    Factory.clear()

@pytest.mark.parametrize("install_test_package", [{
    "name": "tango",
    "path": "tests/dummy_cs/tango"
}], indirect=True)
def test_simulator_bpm_offset(install_test_package):

    ml:PyAML = pyaml("tests/config/bpms.yaml")
    sr:Instrument = ml.get('sr')
    sr.design.get_lattice().disable_6d()
    bpm = sr.design.get_bpm('BPM_C01-01')

    assert bpm.offset.get()[0] == 0
    assert bpm.offset.get()[1] == 0
    bpm.offset.set( np.array([0.1,0.2]) )
    assert bpm.offset.get()[0] == 0.1
    assert bpm.offset.get()[1] == 0.2
    assert np.allclose( bpm.positions.get(), np.array([0.0,0.0]) )

    Factory.clear()

@pytest.mark.parametrize("install_test_package", [{
    "name": "tango",
    "path": "tests/dummy_cs/tango"
}], indirect=True)
def test_simulator_bpm_position(install_test_package):

    ml:PyAML = pyaml("tests/config/bpms.yaml")
    sr:Instrument = ml.get('sr')
    sr.design.get_lattice().disable_6d()
    bpm = sr.design.get_bpm('BPM_C01-01')
    bpm_simple = sr.live.get_bpm('BPM_C01-02')

    assert np.allclose( bpm.positions.get(), np.array([0.0,0.0]) ) 
    assert np.allclose( bpm_simple.positions.get(), np.array([0.0,0.0]) ) 
    
    Factory.clear()
