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

    device.set.side_effect = write
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
def test_operation_uses_set_without_waiting_or_completion_checks(live, device, enabled, operation):
    getattr(live["SOFB"], operation)()

    assert device.mock_calls == [call.set(enabled)]
    assert type(device.set.call_args.args[0]) is bool
    assert live["SOFB"].is_enabled() is enabled
    device.set_and_wait.assert_not_called()
    device.get.assert_not_called()


def test_direct_boolean_accessor_writes_and_reads(live, device):
    switch = live["SOFB"]
    switch.enabled.set(False)
    assert switch.enabled.get() is False
    switch.enabled.set(True)
    assert switch.enabled.get() is True
    assert device.mock_calls == [call.set(False), call.readback(), call.set(True), call.readback()]


@pytest.mark.parametrize("value", [True, False, np.bool_(True), np.bool_(False), 0, 1, 0.0, 1.0, np.int64(1)])
@pytest.mark.parametrize("wrapped", [False, True])
def test_status_returns_native_boolean_from_actual_readback(live, device, value, wrapped):
    device.get.return_value = not bool(value)
    device.readback.return_value = Value(value) if wrapped else value

    assert live["SOFB"].enabled.get() is bool(value)
    assert live["SOFB"].is_enabled() is bool(value)
    device.get.assert_not_called()


@pytest.mark.parametrize(
    "value",
    [2, -1, 0.5, np.nan, "true", "False", None, [True], {"enabled": True}],
)
@pytest.mark.parametrize("wrapped", [False, True])
def test_status_rejects_non_boolean_readback(live, device, value, wrapped):
    device.readback.return_value = Value(value) if wrapped else value

    with pytest.raises(PyAMLException, match="feedback/enabled: expected a boolean flag"):
        live["SOFB"].enabled.get()


@pytest.mark.parametrize("quality", [Quality.INVALID, Quality.ALARM, Quality.CHANGING, Quality.WARNING])
def test_boolean_accessor_adds_no_quality_policy(live, device, quality):
    device.readback.return_value = Value(True, quality=quality)

    assert live["SOFB"].enabled.get() is True


@pytest.mark.parametrize("enabled,operation", [(True, "enable"), (False, "disable")])
def test_write_does_not_claim_completion_or_cache_commanded_state(live, device, enabled, operation):
    device.set.side_effect = None
    device.get.return_value = enabled
    device.readback.return_value = Value(not enabled)

    getattr(live["SOFB"], operation)()

    device.readback.assert_not_called()
    assert live["SOFB"].enabled.get() is not enabled
    device.set_and_wait.assert_not_called()
    device.get.assert_not_called()


@pytest.mark.parametrize("value", [0, 1, 0.0, np.bool_(True), "true", None, [True]])
def test_direct_writes_require_python_boolean(live, device, value):
    with pytest.raises(PyAMLException, match="feedback/enabled: expected a boolean flag"):
        live["SOFB"].enabled.set(value)
    device.set.assert_not_called()


@pytest.mark.parametrize("error", [TimeoutError("timed out"), NotImplementedError("read-only"), OSError("disconnected")])
@pytest.mark.parametrize("operation", ["enable", "disable"])
def test_backend_write_errors_propagate(live, device, error, operation):
    device.set.side_effect = error

    with pytest.raises(type(error)) as exc:
        getattr(live["SOFB"], operation)()

    assert exc.value is error
    device.set_and_wait.assert_not_called()
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
