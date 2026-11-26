import pytest

from pyaml import PyAMLConfigException, PyAMLException
from pyaml.accelerator import Accelerator
from pyaml.configuration import ROOT, NamedValue
from pyaml.configuration.factory import ELEMENT_REGISTRY, Factory
from pyaml.configuration.fileloader import load
from pyaml.validation.validator import SchemaValidator
from tests.conftest import MockElement


def test_factory_build_default():
    """Test default PyAML module loading."""
    data = {"type": "mock_module", "name": "simple"}
    obj = Factory.build(data, False)
    assert isinstance(obj, MockElement)
    assert obj.name == "simple"


@pytest.mark.parametrize("value", [True, {"labels": ["a", "b"]}])
def test_named_value_configuration(value):
    obj = Factory.build(
        SchemaValidator.validate_to_dict({"type": "pyaml.configuration.named_value", "name": "setting", "value": value})
    )
    assert isinstance(obj, NamedValue)
    assert obj.name == "setting"
    assert obj.value == value
    assert type(obj.value) is type(value)
    assert "setting" not in ELEMENT_REGISTRY


def test_named_value_requires_nonempty_name():
    with pytest.raises(PyAMLConfigException, match="nonempty name"):
        NamedValue(" ", 4.0)


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
