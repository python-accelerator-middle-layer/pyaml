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
    magnet1_cfm = sr.design.get_element("QF8B-C04")
    magnet2_cfm = sr.design.get_element("QF8D-C04")
    magnet3_cfm = sr.design.get_element("QD5D-C04")
    magnet4_cfm = sr.design.get_element("QF6D-C04")
    magnet5_cfm = sr.design.get_element("QF4D-C04")

    Factory.clear()
