import pytest
from pyaml import PyAMLConfigException, PyAMLException
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


@pytest.mark.parametrize("test_file", [
    "tests/config/bad_conf.yml",
])
def test_error_location(test_file):
    with pytest.raises(PyAMLConfigException) as exc:
        ml: PyAML = pyaml(test_file)
    print(str(exc.value))
    test_file_names = test_file.split("/")
    test_file_name = test_file_names[len(test_file_names)-1]
    assert f"{test_file_name} at line 7, column 9" in str(exc.value)

@pytest.mark.parametrize("test_file", [
    "tests/config/bad_conf_cycles.yml",
    "tests/config/bad_conf_cycles.json",
])
def test_error_cycles(test_file):
    with pytest.raises(PyAMLException) as exc:
        ml: PyAML = pyaml(test_file)

    assert "A cycle has been detected" in str(exc.value)
