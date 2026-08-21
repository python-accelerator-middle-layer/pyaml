import pytest

from pyaml import PyAMLConfigException, PyAMLException
from pyaml.accelerator import Accelerator
from pyaml.configuration import ROOT
from pyaml.configuration.factory import Factory
from pyaml.configuration.fileloader import load
from tests.conftest import MockElement


def test_factory_build_default():
    """Test default PyAML module loading."""
    data = {"type": "mock_module", "name": "simple"}
    obj = Factory.build(data, False)
    assert isinstance(obj, MockElement)
    assert obj.name == "simple"


@pytest.mark.parametrize(
    "test_file",
    [
        "tests/config/bad_conf_cycles.yml",
        "tests/config/bad_conf_cycles.json",
    ],
)
def test_error_cycles(test_file):
    with pytest.raises(PyAMLException) as exc:
        ml: Accelerator = Accelerator.load(test_file)

    assert "Circular file inclusion of " in str(exc.value)
