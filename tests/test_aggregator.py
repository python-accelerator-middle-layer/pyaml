from pyaml.pyaml import pyaml,PyAML
from pyaml.instrument import Instrument
from pyaml.lattice.element_holder import MagnetType
from pyaml.arrays.magnet_array import MagnetArray
from pyaml.configuration.factory import Factory
import numpy as np
import pytest

@pytest.mark.parametrize("install_test_package", [{
    "name": "tango",
    "path": "tests/dummy_cs/tango"
}], indirect=True)
def test_tune(install_test_package,capfd):

    ml:PyAML = pyaml("tests/config/EBSTune.yaml")
    sr:Instrument = ml.get('sr')

    quadForTuneLive = sr.live.get_magnets("QForTune")
    quadForTuneLive.strengths.set(np.zeros(len(quadForTuneLive)))
    strs = quadForTuneLive.strengths.get()
    out, err = capfd.readouterr()
    assert( "MultiAttribute.set(124 values)" in out )
    assert( "MultiAttribute.get(124 values)" in out )

    Factory.clear()
