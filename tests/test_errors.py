import pytest

from pyaml.accelerator import Accelerator
from pyaml.arrays.magnet_array import MagnetArray
from pyaml.common.exception import PyAMLConfigException, PyAMLException
from pyaml.configuration import ConfigurationManager


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_tune(install_test_package):
    with pytest.raises(PyAMLConfigException) as exc:
        ml: Accelerator = Accelerator.load("tests/config/bad_conf_duplicate_1.yaml")
    assert "MagnetArray HCORR : duplicate name SH1A-C02-H @index 2" in str(exc)

    with pytest.raises(PyAMLConfigException) as exc:
        ml: Accelerator = Accelerator.load("tests/config/bad_conf_duplicate_2.yaml")
    assert "BPMArray BPM : duplicate name BPM_C04-06 @index 3" in str(exc)

    with pytest.raises(PyAMLConfigException) as exc:
        ml: Accelerator = Accelerator.load("tests/config/bad_conf_duplicate_3.yaml")
    assert "Configuration entry 'BPM_C04-06' is duplicated inside category 'devices'" in str(exc)
    assert "bad_conf_duplicate_3.yaml" in str(exc)
    assert "line 58, column 3" in str(exc)

    with pytest.raises(PyAMLConfigException) as exc:
        ml: Accelerator = Accelerator.load("tests/config/bad_conf_duplicate_4.yaml")
    assert "MagnetArray HCORR : duplicate name SH1A-C02-H @index 2" in str(exc)

    sr: Accelerator = Accelerator.load("tests/config/EBSTune.yaml")
    m1 = sr.live.get_magnet("QF1E-C04")
    m2 = sr.design.get_magnet("QF1A-C05")
    with pytest.raises(PyAMLException) as exc:
        ma = MagnetArray("Test", [m1, m2])
    assert "MagnetArray Test: All elements must be attached to the same instance" in str(exc)

    with pytest.raises(PyAMLException) as exc:
        m2 = sr.design.get_magnet("QF1A-C05XX")
    assert "Magnet QF1A-C05XX not defined" in str(exc)

    with pytest.raises(PyAMLException) as exc:
        m2 = sr.design.get_bpm("QF1A-C05XX")
    assert "BPM QF1A-C05XX not defined" in str(exc)


def test_duplicate_error_reports_source_line_and_column_across_files(tmp_path):
    devices_a = tmp_path / "devices_a.yaml"
    devices_a.write_text(
        "- type: test.device\n  name: BPM_DUPLICATE\n",
        encoding="utf-8",
    )
    devices_b = tmp_path / "devices_b.yaml"
    devices_b.write_text(
        "- type: test.device\n  name: BPM_UNIQUE\n- type: test.device\n  name: BPM_DUPLICATE\n",
        encoding="utf-8",
    )
    root = tmp_path / "root.yaml"
    root.write_text(
        "type: pyaml.accelerator\ndevices:\n  - devices_a.yaml\n  - devices_b.yaml\n",
        encoding="utf-8",
    )

    with pytest.raises(PyAMLConfigException) as exc:
        Accelerator.load(str(root))

    message = str(exc.value)
    assert "Configuration entry 'BPM_DUPLICATE' is duplicated inside category 'devices'" in message
    assert f"source '{devices_a}' at line 1, column 3" in message
    assert f"source '{devices_b}' at line 3, column 3" in message


def test_malformed_local_included_yaml_reports_source_line_and_column(tmp_path):
    broken_devices = tmp_path / "broken_devices.yaml"
    broken_devices.write_text(
        "- type: pyaml.bpm.bpm\n  name: BPM_BROKEN\n  model:\n    type: [oops\n",
        encoding="utf-8",
    )
    root = tmp_path / "root.yaml"
    root.write_text(
        "type: pyaml.accelerator\n"
        "facility: ESRF\n"
        "machine: sr\n"
        "energy: 6e9\n"
        "data_folder: /data/store\n"
        "devices: broken_devices.yaml\n",
        encoding="utf-8",
    )

    with pytest.raises(PyAMLException) as exc:
        Accelerator.load(str(root))

    message = str(exc.value)
    assert str(broken_devices) in message
    assert "line 4, column 11" in message


def test_truncated_local_included_json_reports_source_and_position(tmp_path):
    broken_devices = tmp_path / "broken_devices.json"
    broken_devices.write_text(
        '{"type": "pyaml.bpm.bpm", "name": "BPM_BROKEN", "model": ',
        encoding="utf-8",
    )
    root = tmp_path / "root.yaml"
    root.write_text(
        "type: pyaml.accelerator\n"
        "facility: ESRF\n"
        "machine: sr\n"
        "energy: 6e9\n"
        "data_folder: /data/store\n"
        "devices: broken_devices.json\n",
        encoding="utf-8",
    )

    with pytest.raises(PyAMLException) as exc:
        Accelerator.load(str(root))

    message = str(exc.value)
    assert str(broken_devices) in message
    assert "line 1 column" in message


def test_malformed_remote_included_yaml_reports_source_line_and_column(http_config_server):
    routes = {
        "/configs/root.yaml": (
            "type: pyaml.accelerator\n"
            "facility: ESRF\n"
            "machine: sr\n"
            "energy: 6000000000.0\n"
            "data_folder: /data/store\n"
            "devices: fragments/broken_devices.yaml\n"
        ),
        "/configs/fragments/broken_devices.yaml": (
            "- type: pyaml.bpm.bpm\n  name: BPM_BROKEN\n  model:\n    type: [oops\n"
        ),
    }

    with http_config_server(routes) as base_url:
        with pytest.raises(PyAMLConfigException) as exc:
            ConfigurationManager().add(f"{base_url}/configs/root.yaml")

    message = str(exc.value)
    assert f"{base_url}/configs/fragments/broken_devices.yaml" in message
    assert "line 4, column 11" in message


def test_truncated_remote_included_json_reports_source_and_position(http_config_server):
    routes = {
        "/configs/root.yaml": (
            "type: pyaml.accelerator\n"
            "facility: ESRF\n"
            "machine: sr\n"
            "energy: 6000000000.0\n"
            "data_folder: /data/store\n"
            "devices: fragments/broken_devices.json\n"
        ),
        "/configs/fragments/broken_devices.json": (
            '{"type": "pyaml.bpm.bpm", "name": "BPM_BROKEN", "model": ',
            "application/json",
            200,
        ),
    }

    with http_config_server(routes) as base_url:
        with pytest.raises(PyAMLConfigException) as exc:
            ConfigurationManager().add(f"{base_url}/configs/root.yaml")

    message = str(exc.value)
    assert f"{base_url}/configs/fragments/broken_devices.json" in message
    assert "line 1 column" in message
