from pyaml.configuration.factory import depthFirstBuild
from tests.conftest import MockElement


def test_factory_build_default():
    """Test default PyAML module loading."""
    data = {
        "type": "mock_module",
        "name": "simple"
    }
    obj = depthFirstBuild(data)
    assert isinstance(obj, MockElement)
    assert obj.name == "simple"


def test_factory_with_custom_strategy():
    """Test that custom BuildStrategy overrides default logic."""
    data = {
        "type": "mock_module",
        "name": "injected",
        "custom": True
    }
    obj = depthFirstBuild(data)
    assert isinstance(obj, MockElement)
    assert obj.name == "custom_injected"
