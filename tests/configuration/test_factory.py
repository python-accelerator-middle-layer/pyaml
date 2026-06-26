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
        "tests/config/bad_conf.yml",
    ],
)
def test_error_location(test_file):
    previous_root = ROOT.get()
    try:
        with pytest.raises(PyAMLConfigException) as exc:
            ROOT.set("tests/config")
            cfg = load("bad_conf.yml")
            Factory.build(cfg, False)
    finally:
        ROOT.set(previous_root)
    print(str(exc.value))
    test_file_names = test_file.split("/")
    test_file_name = test_file_names[len(test_file_names) - 1]
    assert f"{test_file_name} at line 6, column 5" in str(exc.value)


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
    if not test_file.endswith(".json"):
        assert "at line 22" in str(exc.value)
