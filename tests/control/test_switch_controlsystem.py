from unittest.mock import call, create_autospec

import numpy as np
import pytest

from pyaml.common.exception import PyAMLException
from pyaml.common.switch_element import SwitchElement
from pyaml.control.controlsystem import ControlSystemAdapter
from pyaml.control.deviceaccess import DeviceAccess
from pyaml.control.readback_value import Quality, Value


@pytest.fixture
def device():
    device = create_autospec(DeviceAccess, instance=True)
    device.name.return_value = "feedback/enabled"
    device.readback.return_value = Value(True)

    def write(value):
        device.readback.return_value = Value(value)

    device.set_and_wait.side_effect = write
    return device


@pytest.fixture
def live(device, monkeypatch):
    holder = ControlSystemAdapter()
    monkeypatch.setattr(holder, "name", lambda: "live")
    monkeypatch.setattr(holder, "get_device_access", lambda ref: device)
    holder.fill_device([SwitchElement("SOFB", "SOFB_ENABLED")])
    return holder


def test_attachment_and_representation_do_not_access_channel(live, device):
    repr(live["SOFB"])
    live.post_init()

    assert device.mock_calls == []


@pytest.mark.parametrize("enabled,operation", [(True, "enable"), (False, "disable")])
def test_operation_waits_then_verifies_actual_readback(live, device, enabled, operation):
    getattr(live["SOFB"], operation)()

    assert device.mock_calls == [call.set_and_wait(enabled), call.readback()]
    assert type(device.set_and_wait.call_args.args[0]) is bool
    assert live["SOFB"].is_enabled() is enabled
    device.set.assert_not_called()
    device.get.assert_not_called()


@pytest.mark.parametrize("value", [True, False, np.bool_(True), np.bool_(False)])
@pytest.mark.parametrize("wrapped", [False, True])
def test_status_returns_native_boolean_from_actual_readback(live, device, value, wrapped):
    device.get.return_value = not bool(value)
    device.readback.return_value = Value(value) if wrapped else value

    assert live["SOFB"].is_enabled() is bool(value)
    device.get.assert_not_called()


@pytest.mark.parametrize(
    "value",
    [0, 1, 0.0, 1.0, np.int64(1), np.float64(0), "true", "False", None, [True], np.array([True]), np.array(True)],
)
@pytest.mark.parametrize("wrapped", [False, True])
def test_status_rejects_non_boolean_readback(live, device, value, wrapped):
    device.readback.return_value = Value(value) if wrapped else value

    with pytest.raises(PyAMLException, match="feedback/enabled: expected boolean readback"):
        live["SOFB"].is_enabled()


@pytest.mark.parametrize("quality", [Quality.INVALID, Quality.ALARM, Quality.CHANGING, Quality.WARNING])
@pytest.mark.parametrize("operation", ["enable", "disable", "is_enabled"])
def test_non_valid_quality_is_not_reported_as_success(live, device, quality, operation):
    device.set_and_wait.side_effect = None
    device.readback.return_value = Value(True, quality=quality)

    with pytest.raises(PyAMLException, match=f"feedback/enabled: expected VALID boolean readback, got quality {quality}"):
        getattr(live["SOFB"], operation)()


@pytest.mark.parametrize("enabled,operation", [(True, "enable"), (False, "disable")])
def test_confirmation_mismatch_raises(live, device, enabled, operation):
    device.set_and_wait.side_effect = None
    device.get.return_value = enabled
    device.readback.return_value = Value(not enabled)

    with pytest.raises(PyAMLException, match=f"SOFB: readback did not confirm enabled={enabled}"):
        getattr(live["SOFB"], operation)()

    device.get.assert_not_called()


@pytest.mark.parametrize("operation", ["enable", "disable"])
def test_non_boolean_confirmation_raises(live, device, operation):
    device.set_and_wait.side_effect = None
    device.readback.return_value = Value(1)

    with pytest.raises(PyAMLException, match="expected boolean readback"):
        getattr(live["SOFB"], operation)()


@pytest.mark.parametrize("error", [TimeoutError("timed out"), NotImplementedError("cannot wait"), OSError("disconnected")])
@pytest.mark.parametrize("operation", ["enable", "disable"])
def test_backend_wait_errors_propagate_without_fallback(live, device, error, operation):
    device.set_and_wait.side_effect = error

    with pytest.raises(type(error)) as exc:
        getattr(live["SOFB"], operation)()

    assert exc.value is error
    device.set.assert_not_called()
    device.readback.assert_not_called()


def test_readback_errors_propagate(live, device):
    error = OSError("read failed")
    device.readback.side_effect = error

    with pytest.raises(OSError) as exc:
        live["SOFB"].is_enabled()

    assert exc.value is error


def test_missing_device_is_rejected(monkeypatch):
    holder = ControlSystemAdapter()
    monkeypatch.setattr(holder, "get_device_access", lambda ref: None)

    with pytest.raises(PyAMLException, match="SOFB: switch channel 'MISSING' is unavailable"):
        holder.fill_device([SwitchElement("SOFB", "MISSING")])

    assert holder.get().names() == []


def test_device_resolution_errors_propagate(monkeypatch):
    holder = ControlSystemAdapter()
    resolver = create_autospec(holder.get_device_access, side_effect=OSError("lookup failed"))
    monkeypatch.setattr(holder, "get_device_access", resolver)

    with pytest.raises(OSError, match="lookup failed"):
        holder.fill_device([SwitchElement("SOFB", "SOFB_ENABLED")])

    resolver.assert_called_once_with("SOFB_ENABLED")


def test_duplicate_registration_does_not_replace_element(live):
    original = live["SOFB"]

    with pytest.raises(PyAMLException, match="Duplicate element"):
        live.fill_device([SwitchElement("SOFB", "OTHER_CHANNEL")])

    assert live["SOFB"] is original
