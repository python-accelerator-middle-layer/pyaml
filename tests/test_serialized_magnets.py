import pytest

from pyaml.pyaml import pyaml,PyAML
from pyaml.configuration.factory import Factory
from pyaml.instrument import Instrument

@pytest.mark.parametrize("sr_file", [
    "tests/config/sr_serialized_magnets.yaml",
])
def test_config_load(sr_file):
    ml:PyAML = pyaml(sr_file)
    sr:Instrument = ml.get('sr')

    Factory.clear()
