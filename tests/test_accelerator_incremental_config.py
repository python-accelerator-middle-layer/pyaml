import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np
import pytest

from pyaml import PyAMLConfigException, PyAMLException
from pyaml.accelerator import Accelerator


def _control_fragment(name: str = "live", tango_host: str = "dummy:10000") -> dict:
    return {
        "controls": [
            {
                "type": "tango.pyaml.controlsystem",
                "name": name,
                "tango_host": tango_host,
            }
        ]
    }


def _bpm_fragment(name: str = "BPM_TEST") -> dict:
    return {
        "devices": [
            {
                "type": "pyaml.bpm.bpm",
                "name": name,
                "model": {
                    "type": "pyaml.bpm.bpm_simple_model",
                    "x_pos": {
                        "type": "tango.pyaml.attribute",
                        "attribute": f"test/{name}/x",
                        "unit": "mm",
                    },
                    "y_pos": {
                        "type": "tango.pyaml.attribute",
                        "attribute": f"test/{name}/y",
                        "unit": "mm",
                    },
                },
            }
        ]
    }


class _PayloadHandler(BaseHTTPRequestHandler):
    payload = {}

    def do_GET(self):
        body = json.dumps(self.payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


@pytest.fixture
def config_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _PayloadHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_add_and_remove_config_updates_live_accelerator(install_test_package):
    acc = Accelerator.empty()

    acc.add_config(_control_fragment())
    assert "live" in acc.controls()
    assert acc.live is not None

    acc.add_config(_bpm_fragment())
    assert acc.live.get_bpm("BPM_TEST").get_name() == "BPM_TEST"

    acc.remove_config({"devices": [{"name": "BPM_TEST"}]})
    with pytest.raises(PyAMLException, match="BPM BPM_TEST not defined"):
        acc.live.get_bpm("BPM_TEST")


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_add_config_from_file(install_test_package, tmp_path):
    control_file = tmp_path / "control.yaml"
    control_file.write_text(
        "controls:\n  - type: tango.pyaml.controlsystem\n    name: live\n    tango_host: dummy:10000\n",
        encoding="utf-8",
    )

    device_file = tmp_path / "device.yaml"
    device_file.write_text(
        "devices:\n"
        "  - type: pyaml.bpm.bpm\n"
        "    name: BPM_FILE\n"
        "    model:\n"
        "      type: pyaml.bpm.bpm_simple_model\n"
        "      x_pos:\n"
        "        type: tango.pyaml.attribute\n"
        "        attribute: test/BPM_FILE/x\n"
        "        unit: mm\n"
        "      y_pos:\n"
        "        type: tango.pyaml.attribute\n"
        "        attribute: test/BPM_FILE/y\n"
        "        unit: mm\n",
        encoding="utf-8",
    )

    acc = Accelerator.empty()
    acc.add_config(control_file)
    acc.add_config(device_file)

    assert acc.live.get_bpm("BPM_FILE").get_name() == "BPM_FILE"


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_fetch_config_and_add_config_from_url_with_key(install_test_package, config_server):
    _PayloadHandler.payload = {
        "controls": [
            {
                "type": "tango.pyaml.controlsystem",
                "name": "live_shadow",
                "tango_host": "shadow:10000",
            },
            {
                "type": "tango.pyaml.controlsystem",
                "name": "other",
                "tango_host": "other:10000",
            },
        ]
    }
    url = f"http://127.0.0.1:{config_server.server_port}/config"

    fragment = Accelerator.fetch_config(url, key="controls.live_shadow")
    assert fragment["name"] == "live_shadow"

    acc = Accelerator.empty()
    acc.add_config(url, key="controls.live_shadow")
    assert "live_shadow" in acc.controls()
    assert "other" not in acc.controls()

    acc.remove_config(url, key="controls.live_shadow")
    assert "live_shadow" not in acc.controls()


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_add_config_failure_rolls_back_state(install_test_package):
    acc = Accelerator.empty()
    acc.add_config(_control_fragment())
    acc.add_config(_bpm_fragment())

    snapshot = acc.to_dict()

    with pytest.raises(PyAMLConfigException):
        acc.add_config({"devices": [{"type": "pyaml.bpm.bpm", "name": "BROKEN"}]})

    assert acc.to_dict() == snapshot
    assert acc.live.get_bpm("BPM_TEST").get_name() == "BPM_TEST"


def test_add_config_accumulates_device_lists():
    acc = Accelerator.empty(ignore_external=True)

    acc.add_config("tests/config/incremental_base.yaml")
    assert len(acc.design.get_all_magnets()) == 0
    assert len(acc.design.get_all_bpms()) == 0

    acc.add_config("tests/config/incremental_devices_magnets_part1.yaml")
    assert len(acc.design.get_all_magnets()) == 2
    assert acc.design.get_magnet("QF1E-C04").get_name() == "QF1E-C04"
    assert acc.design.get_magnet("QF1A-C05").get_name() == "QF1A-C05"

    acc.add_config("tests/config/incremental_devices_magnets_part2.yaml")
    assert len(acc.design.get_all_magnets()) == 4
    assert acc.design.get_magnet("QF1E-C04").get_name() == "QF1E-C04"
    assert acc.design.get_magnet("QF1A-C05").get_name() == "QF1A-C05"
    assert acc.design.get_magnet("QF1E-C05").get_name() == "QF1E-C05"
    assert acc.design.get_magnet("QF1A-C06").get_name() == "QF1A-C06"

    acc.add_config("tests/config/incremental_devices_bpms_part1.yaml")
    assert len(acc.design.get_all_magnets()) == 4
    assert len(acc.design.get_all_bpms()) == 2
    assert acc.design.get_bpm("BPM_C04-01").get_name() == "BPM_C04-01"
    assert acc.design.get_bpm("BPM_C04-02").get_name() == "BPM_C04-02"
    assert acc.design.get_magnet("QF1E-C04").get_name() == "QF1E-C04"


def test_add_config_array_with_missing_elements_raises_and_rolls_back():
    acc = Accelerator.empty(ignore_external=True)

    acc.add_config("tests/config/incremental_base.yaml")
    acc.add_config("tests/config/incremental_devices_magnets_part1.yaml")
    snapshot = acc.to_dict()

    with pytest.raises(PyAMLConfigException, match="Magnet DOES_NOT_EXIST not defined"):
        acc.add_config("tests/config/incremental_arrays_missing.yaml")

    assert acc.to_dict() == snapshot
    with pytest.raises(PyAMLException, match="Magnet array QMissing not defined"):
        acc.design.get_magnets("QMissing")


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_add_config_accumulates_controls_without_removing_previous_ones(install_test_package):
    acc = Accelerator.empty()

    acc.add_config("tests/config/incremental_base.yaml")
    acc.add_config("tests/config/incremental_devices_magnets_part1.yaml")
    acc.add_config("tests/config/incremental_devices_bpms_part1.yaml")

    acc.add_config("tests/config/incremental_controls_live.yaml")
    assert set(acc.controls().keys()) == {"live"}
    assert acc.live.get_magnet("QF1E-C04").get_name() == "QF1E-C04"
    assert acc.live.get_bpm("BPM_C04-01").get_name() == "BPM_C04-01"

    acc.add_config("tests/config/incremental_controls_shadow.yaml")
    assert set(acc.controls().keys()) == {"live", "live_shadow"}
    assert acc.live.get_magnet("QF1E-C04").get_name() == "QF1E-C04"
    assert acc.live.get_bpm("BPM_C04-02").get_name() == "BPM_C04-02"
    assert acc.live_shadow.get_magnet("QF1A-C05").get_name() == "QF1A-C05"
    assert acc.live_shadow.get_bpm("BPM_C04-01").get_name() == "BPM_C04-01"

    live_quad = acc.live.get_magnet("QF1E-C04")
    shadow_quad = acc.live_shadow.get_magnet("QF1E-C04")

    live_quad.strength.set(1.0e-4)
    assert np.isclose(live_quad.strength.get(), 1.0e-4, atol=1e-10)
    assert not np.isclose(live_quad.hardware.get(), 0.0, atol=1e-12)
    assert np.isclose(shadow_quad.strength.get(), 0.0, atol=1e-12)

    shadow_quad.hardware.set(12.34)
    assert np.isclose(shadow_quad.hardware.get(), 12.34, atol=1e-10)
    assert np.isclose(live_quad.strength.get(), 1.0e-4, atol=1e-10)
