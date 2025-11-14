import pytest

from pyaml.pyaml import pyaml,PyAML
from pyaml.configuration.factory import Factory
from pyaml.instrument import Instrument

@pytest.mark.parametrize(
    ("sr_file", "install_test_package"),
    [
        ("tests/config/sr_serialized_magnets.yaml", {"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}),
    ],
    indirect=["install_test_package"],
)
def test_config_load(sr_file, install_test_package):
    ml:PyAML = pyaml(sr_file)
    sr:Instrument = ml.get('sr')
    assert sr is not None
    Factory.clear()
