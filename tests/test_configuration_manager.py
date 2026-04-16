from pathlib import Path

import pytest

from pyaml import PyAMLConfigException
from pyaml.accelerator import Accelerator
from pyaml.configuration import ConfigurationManager


def test_configuration_manager_add_from_dict(
    simulator_fragment_factory,
    ebs_lattice_file,
):
    manager = ConfigurationManager()

    result = manager.add(
        {
            "facility": "Dict Facility",
            "machine": "dict_ring",
            "energy": 3.0e9,
            "data_folder": "data",
            "simulators": [simulator_fragment_factory("design")],
            "devices": [],
        },
        source_name="dict-fixture",
    )

    assert result is None
    assert manager.categories() == ["simulators"]
    assert manager.keys() == ["design"]
    assert manager.keys("simulators") == ["design"]
    assert manager.has("simulators", "design")
    assert manager.find("des*") == ["design"]
    assert manager.get("simulators", "design")["lattice"] == str(ebs_lattice_file)


def test_configuration_manager_add_from_yaml_and_json(
    config_manager_base_config,
    config_manager_simulator_json,
):
    manager = ConfigurationManager()

    manager.add(config_manager_base_config)
    manager.add(config_manager_simulator_json)

    assert manager.categories() == ["simulators"]
    assert manager.keys("simulators") == ["design", "analysis"]
    assert Path(manager.get("simulators", "design")["lattice"]).is_absolute()
    assert manager.get("simulators", "analysis")["description"] == "Secondary simulation mode"


def test_configuration_manager_remove_named_entry(
    config_manager_base_config,
    simulator_fragment_factory,
):
    manager = ConfigurationManager()
    manager.add(config_manager_base_config)
    manager.add({"simulators": [simulator_fragment_factory("tracking")]})

    result = manager.remove("simulators", "tracking")

    assert result is None
    assert manager.keys("simulators") == ["design"]
    assert not manager.has("simulators", "tracking")


def test_configuration_manager_replace_named_entry(
    config_manager_base_config,
    ebs_lattice_file,
):
    manager = ConfigurationManager()
    manager.add(config_manager_base_config)

    result = manager.replace(
        "simulators",
        {
            "type": "pyaml.lattice.simulator",
            "name": "design",
            "lattice": str(ebs_lattice_file),
            "description": "Replaced simulator",
        },
    )

    assert result is None
    assert manager.get("simulators", "design")["description"] == "Replaced simulator"


def test_configuration_manager_clear_category_and_settings(
    config_manager_base_config,
    simulator_fragment_factory,
):
    manager = ConfigurationManager()
    manager.add(config_manager_base_config)
    manager.add({"simulators": [simulator_fragment_factory("tracking")]})

    result = manager.clear("simulators")

    assert result is None
    assert manager.keys("simulators") == []
    assert manager.categories() == []
    assert manager.settings()["facility"] == "Test Facility"

    result = manager.clear()

    assert result is None
    assert manager.to_dict() == {"type": "pyaml.accelerator"}


def test_configuration_manager_settings_follow_accelerator_config_model_order():
    manager = ConfigurationManager()
    manager.add(
        {
            "facility": "Test Facility",
            "machine": "ring",
            "energy": 3.0e9,
            "alphac": 1.0e-4,
            "data_folder": "data",
            "description": "Ordered settings",
            "devices": [],
        }
    )

    assert list(manager.settings()) == [
        "type",
        "facility",
        "machine",
        "energy",
        "alphac",
        "data_folder",
        "description",
    ]


def test_configuration_manager_to_dict_snapshot_can_be_reloaded(
    config_manager_base_config,
    simulator_fragment_factory,
):
    manager = ConfigurationManager()
    manager.add(config_manager_base_config)
    manager.add({"simulators": [simulator_fragment_factory("tracking")]})

    snapshot = manager.to_dict()

    reloaded = ConfigurationManager()
    reloaded.add(snapshot)

    assert reloaded.to_dict() == snapshot


def test_configuration_manager_build_explicitly(
    config_manager_base_config,
    simulator_fragment_factory,
):
    manager = ConfigurationManager()
    manager.add(config_manager_base_config)
    manager.add({"simulators": [simulator_fragment_factory("tracking")]})

    accelerator = manager.build()

    assert isinstance(accelerator, Accelerator)
    assert accelerator.design.name() == "design"
    assert accelerator.simulators()["tracking"].name() == "tracking"


def test_configuration_manager_accumulates_multiple_device_fragments(
    sr_base_fragment,
    sr_devices_fragment,
    tune_monitor_devices_fragment,
):
    manager = ConfigurationManager()
    manager.add(sr_base_fragment)
    manager.add(sr_devices_fragment)
    manager.add(tune_monitor_devices_fragment)

    assert manager.categories() == ["controls", "simulators", "devices"]
    assert manager.keys("devices") == [
        "QF1A-C01",
        "SH1A-C01",
        "SH1A-C02",
        "BPM_C04-01",
        "BPM_C04-02",
        "BETATRON_TUNE",
    ]
    assert manager.has("devices", "QF1A-C01")
    assert manager.has("devices", "SH1A-C01")
    assert manager.has("devices", "SH1A-C02")
    assert manager.has("devices", "BPM_C04-01")
    assert manager.has("devices", "BPM_C04-02")
    assert manager.has("devices", "BETATRON_TUNE")
    assert manager.get("devices", "QF1A-C01")["type"] == "pyaml.magnet.quadrupole"
    assert manager.get("devices", "SH1A-C01")["type"] == "pyaml.magnet.cfm_magnet"
    assert manager.get("devices", "BPM_C04-01")["type"] == "pyaml.bpm.bpm"
    assert manager.get("devices", "BETATRON_TUNE")["type"] == "pyaml.diagnostics.tune_monitor"


def test_accelerator_load_stays_compatible(config_manager_base_config):
    accelerator = Accelerator.load(config_manager_base_config)

    assert isinstance(accelerator, Accelerator)
    assert accelerator.design.name() == "design"
    assert accelerator.get_description() == "Base configuration for ConfigurationManager tests"


def test_configuration_manager_rejects_duplicate_names(
    config_manager_base_config,
    simulator_fragment_factory,
):
    manager = ConfigurationManager()
    manager.add(config_manager_base_config)

    with pytest.raises(PyAMLConfigException, match="already exists in category 'simulators'"):
        manager.add({"simulators": [simulator_fragment_factory("design")]})


def test_configuration_manager_rejects_rest_source_explicitly():
    manager = ConfigurationManager()

    with pytest.raises(PyAMLConfigException, match="REST configuration sources are not implemented yet"):
        manager.add("https://example.org/config")


def test_configuration_manager_repr_is_yellow_pages_like(
    sr_base_fragment,
    sr_arrays_fragment,
    sr_devices_fragment,
):
    manager = ConfigurationManager()
    manager.add(sr_base_fragment)
    manager.add(sr_arrays_fragment)
    manager.add(sr_devices_fragment)

    output = repr(manager)

    assert str(manager) == output
    assert "Settings:" in output
    assert "Controls:" in output
    assert "Simulators:" in output
    assert "Arrays:" in output
    assert "Devices:" in output
    assert "live (tango.pyaml.controlsystem) source=config_manager_sr_base.yaml" in output
    assert "design (pyaml.lattice.simulator) source=config_manager_sr_base.yaml" in output
    assert "HCORR (pyaml.arrays.magnet) patterns=1 source=config_manager_sr_arrays.yaml" in output
    assert "BPM_C04-01 (pyaml.bpm.bpm) source=config_manager_sr_devices.yaml" in output
    assert "    ." in output


def test_configuration_manager_yellow_pages_like_shortcuts(
    sr_base_fragment,
    sr_arrays_fragment,
    sr_devices_fragment,
):
    manager = ConfigurationManager()
    manager.add(sr_base_fragment)
    manager.add(sr_arrays_fragment)
    manager.add(sr_devices_fragment)

    assert manager["BPM_C04*"] == ["BPM_C04-01", "BPM_C04-02"]
    assert manager.HCORR["type"] == "pyaml.arrays.magnet"
    assert manager.simulators == ["design"]
