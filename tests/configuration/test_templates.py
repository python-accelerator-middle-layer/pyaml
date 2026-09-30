import json

import pytest
import yaml

from pyaml import PyAMLException
from pyaml.accelerator import Accelerator
from pyaml.common.exception import PyAMLConfigException
from pyaml.configuration import ConfigurationManager
from pyaml.configuration.fileloader import FIELD_LOCATIONS_KEY, ROOT, load
from pyaml.configuration.template import TemplateManager


def _template_definition(prefix=""):
    return {
        "name": "device",
        "parameters": ["name"],
        "config": {"class": "pyaml.magnet.hcorrector.HCorrector", "name": prefix + "{name}"},
    }


def _write_config(path, config):
    path.write_text(json.dumps(config) if path.suffix == ".json" else yaml.safe_dump(config, sort_keys=False))
    return path


@pytest.fixture
def template_config_root(tmp_path):
    previous_root = ROOT.get()
    ROOT.set(tmp_path)
    try:
        yield tmp_path
    finally:
        ROOT.set(previous_root)


def test_template_definitions_are_independent_of_inputs_and_results():
    registry = TemplateManager()
    parameters = ["name"]
    config = {"name": "{name}", "nested": [1]}
    registry.add("T", parameters, config)

    parameters.clear()
    config["nested"].append(2)

    generated = registry.generate("T", "Q1")
    assert generated == {"name": "Q1", "nested": [1]}

    generated["nested"].append(3)

    assert registry.generate("T", "Q2") == {"name": "Q2", "nested": [1]}


def test_template_registry_rejects_duplicate_names():
    registry = TemplateManager()
    registry.add("T", ["name"], {"name": "{name}"})

    with pytest.raises(PyAMLConfigException, match="Template 'T'.*registered"):
        registry.add("T", [], {})


@pytest.mark.parametrize("suffix", [".yaml", ".json"])
def test_standalone_loads_have_fresh_template_registries(tmp_path, suffix):
    path = _write_config(
        tmp_path / ("config" + suffix),
        {"templates": [_template_definition()], "devices": ["${template:device,Q1}"]},
    )

    first = load(str(path))
    second = load(str(path))

    assert first["devices"][0]["name"] == "Q1"
    assert second["devices"][0]["name"] == "Q1"

    use_only = _write_config(tmp_path / "use.yaml", {"devices": ["${template:device,Q1}"]})
    with pytest.raises(PyAMLException, match="Invalid template resolver call"):
        load(str(use_only))


def test_configuration_managers_have_independent_templates(tmp_path):
    first_definitions = _write_config(tmp_path / "first.yaml", {"templates": [_template_definition("first-")]})
    second_definitions = _write_config(tmp_path / "second.json", {"templates": [_template_definition("second-")]})
    usage = _write_config(tmp_path / "usage.yaml", {"devices": ["${template:device,Q1}"]})
    first = ConfigurationManager()
    second = ConfigurationManager()

    first.add(first_definitions)
    second.add(second_definitions)
    first.add(usage)
    second.add(usage)

    assert first.keys("devices") == ["first-Q1"]
    assert second.keys("devices") == ["second-Q1"]

    first.clear()
    second.clear("devices")
    second.add(usage)

    assert second.keys("devices") == ["second-Q1"]


def test_manager_category_clear_preserves_templates(tmp_path):
    definitions = _write_config(tmp_path / "definitions.yaml", {"templates": [_template_definition()]})
    usage = _write_config(tmp_path / "usage.yaml", {"devices": ["${template:device,Q1}"]})
    manager = ConfigurationManager()
    manager.add(definitions)
    manager.add(usage)

    manager.clear("devices")
    manager.add(usage)

    assert manager.keys("devices") == ["Q1"]


def test_manager_clear_resets_template_registration(tmp_path):
    definitions = _write_config(tmp_path / "definitions.yaml", {"templates": [_template_definition()]})
    usage = _write_config(tmp_path / "usage.yaml", {"devices": ["${template:device,Q1}"]})
    manager = ConfigurationManager()
    manager.add(definitions)

    manager.clear()

    with pytest.raises(PyAMLException, match="Invalid template resolver call"):
        manager.add(usage)

    manager.add(definitions)
    manager.add(usage)

    assert manager.keys("devices") == ["Q1"]


def test_included_files_and_nested_templates_share_registry(template_config_root, monkeypatch):
    tmp_path = template_config_root
    monkeypatch.setenv("PYAML_TEST_HOST", "localhost")
    _write_config(tmp_path / "definitions.yaml", {"templates": [_template_definition()]})
    _write_config(tmp_path / "Q1.json", {"factor": 1.5})
    path = _write_config(
        tmp_path / "parent.yaml",
        {
            "templates": [
                {
                    "name": "wrapper",
                    "parameters": ["name"],
                    "config": {
                        "device": "${template:device,{name}}",
                        "model": "{name}.json",
                        "host": "${env:PYAML_TEST_HOST}",
                    },
                }
            ],
            "definitions": "definitions.yaml",
            "result": "${template:wrapper,Q1}",
        },
    )

    loaded = load(str(path), include_locations=True)
    result = loaded["result"]

    assert result["device"]["name"] == "Q1"
    assert result["model"] == {"factor": 1.5}
    assert result["host"] == "localhost"
    assert "templates" in loaded[FIELD_LOCATIONS_KEY]
    assert "name" in result["device"][FIELD_LOCATIONS_KEY]


def test_explicit_registry_can_be_shared_between_standalone_loads(tmp_path):
    registry = TemplateManager()
    definitions = _write_config(tmp_path / "definitions.yaml", {"templates": [_template_definition()]})
    usage = _write_config(tmp_path / "usage.json", {"devices": ["${template:device,Q1}"]})

    load(str(definitions), templates=registry)
    result = load(str(usage), templates=registry)

    assert result["devices"][0]["name"] == "Q1"


def test_recursive_template_still_reports_configuration_error(tmp_path):
    path = _write_config(
        tmp_path / "recursive.yaml",
        {
            "templates": [{"name": "T", "parameters": ["name"], "config": {"child": "${template:T,{name}}"}}],
            "result": "${template:T,Q1}",
        },
    )

    with pytest.raises(PyAMLException, match="Recursion limit reached while expanding template"):
        load(str(path))


def test_accelerator_load_does_not_clear_an_existing_managers_templates(template_config_root):
    tmp_path = template_config_root
    definitions = _write_config(tmp_path / "definitions.yaml", {"templates": [_template_definition()]})
    manager = ConfigurationManager()
    manager.add(definitions)
    accelerator = _write_config(
        tmp_path / "accelerator.yaml",
        {
            "class": "pyaml.accelerator.Accelerator",
            "facility": "test",
            "machine": "sr",
            "energy": 3e9,
            "templates": [_template_definition("other-")],
        },
    )
    usage = _write_config(tmp_path / "usage.yaml", {"devices": ["${template:device,Q1}"]})

    for _ in range(2):
        Accelerator.load(str(accelerator))
    manager.add(usage)

    assert manager.keys("devices") == ["Q1"]
