import pytest

import pyaml
from pyaml.accelerator import Accelerator



@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_ranges_array(install_test_package):
    sr: Accelerator = Accelerator.load("tests/config/EBSTune-range.yaml")
    mag = sr.live.get_magnets("QForTune").strengths
    with pytest.raises(pyaml.PyAMLException, match="out of range"):
        mag.set( mag.get()*1000.0 )
