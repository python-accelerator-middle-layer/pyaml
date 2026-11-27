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


def test_commands_and_accessor_write_without_waiting_and_read_actual_state(live, device):
    switch = live["SOFB"]
    device.readback.return_value = Value(False)

    switch.enable()
    assert switch.enabled.get() is False
    device.readback.return_value = Value(True)
    switch.disable()
    assert switch.is_enabled() is True
    switch.enabled.set(False)
    assert switch.enabled.get() is True
    device.readback.return_value = Value(False)
    assert switch.is_enabled() is False

    assert device.mock_calls == [
        call.set(True),
        call.readback(),
        call.set(False),
        call.readback(),
        call.set(False),
        call.readback(),
        call.readback(),
    ]
    device.set_and_wait.assert_not_called()
    device.get.assert_not_called()


@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param(False, False, id="boolean"),
        pytest.param(Value(True, quality=Quality.INVALID), True, id="wrapped-boolean-invalid-quality"),
        pytest.param(0, False, id="numeric-zero"),
        pytest.param(Value(1), True, id="wrapped-numeric-one"),
        pytest.param(np.bool_(True), True, id="numpy-boolean"),
    ],
)
def test_status_returns_native_boolean_from_actual_readback(live, device, value, expected):
    device.get.return_value = not expected
    device.readback.return_value = value

    assert live["SOFB"].enabled.get() is expected
    device.get.assert_not_called()


@pytest.mark.parametrize(
    "value", [pytest.param(2, id="numeric"), pytest.param(Value("off"), id="wrapped-string"), pytest.param(None, id="missing")]
)
def test_status_rejects_non_boolean_readback(live, device, value):
    device.readback.return_value = value

    with pytest.raises(PyAMLException, match="feedback/enabled: expected a boolean flag"):
        live["SOFB"].enabled.get()


@pytest.mark.parametrize("value", [1, np.bool_(True), "true"])
def test_direct_writes_require_python_boolean(live, device, value):
    with pytest.raises(PyAMLException, match="feedback/enabled: expected a boolean flag"):
        live["SOFB"].enabled.set(value)
    device.set.assert_not_called()


def test_backend_write_errors_propagate(live, device):
    error = OSError("disconnected")
    device.set.side_effect = error

    with pytest.raises(OSError) as exc:
        live["SOFB"].enable()

    assert exc.value is error
    device.set_and_wait.assert_not_called()
    device.readback.assert_not_called()


def test_readback_errors_propagate(live, device):
    error = OSError("read failed")
    device.readback.side_effect = error

    with pytest.raises(OSError) as exc:
        live["SOFB"].is_enabled()

    assert exc.value is error


@pytest.mark.parametrize("operation,args", [("get", ()), ("set", (True,))])
def test_missing_device_is_rejected_only_on_access(monkeypatch, operation, args):
    holder = ControlSystemAdapter()
    resolver = create_autospec(holder.get_device_access, return_value=None)
    monkeypatch.setattr(holder, "get_device_access", resolver)
    holder.fill_device([SwitchElement("SOFB", "MISSING")])
    switch = holder["SOFB"]

    assert switch.peer is holder
    repr(switch)
    holder.post_init()

    with pytest.raises(PyAMLException, match="SOFB: switch channel 'MISSING' is unavailable"):
        getattr(switch.enabled, operation)(*args)

    resolver.assert_called_once_with("MISSING")


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
