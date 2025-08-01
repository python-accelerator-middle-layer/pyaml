import pytest
from pyaml import PyAMLConfigException
from pyaml.configuration.factory import Factory
from pyaml.pyaml import PyAML, pyaml
from tests.conftest import MockElement


def test_factory_build_default():
    """Test default PyAML module loading."""
    data = {
        "type": "mock_module",
        "name": "simple"
    }
    obj = Factory.depth_first_build(data)
    assert isinstance(obj, MockElement)
    assert obj.name == "simple"


def test_factory_with_custom_strategy():
    """Test that custom BuildStrategy overrides default logic."""
    data = {
        "type": "mock_module",
        "name": "injected",
        "custom": True
    }
    obj = Factory.depth_first_build(data)
    assert isinstance(obj, MockElement)
    assert obj.name == "custom_injected"


def test_error_location():

    with pytest.raises(PyAMLConfigException) as exc:
        ml: PyAML = pyaml("tests/config/bad_conf.yml")

    assert "at line 7, column 9" in str(exc.value)
