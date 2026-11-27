from unittest.mock import Mock

import numpy as np
import pytest

from pyaml import PyAMLException
from pyaml.arrays.magnet_array import MagnetArray
from pyaml.control.abstract_impl import RWStrengthTrim
from pyaml.control.controlsystem import ControlSystemAdapter
from pyaml.control.deviceaccess import DeviceAccess
from pyaml.control.deviceaccesslist import DeviceAccessList
from pyaml.magnet.inline_curve import InlineCurve
from pyaml.magnet.linear_serialized_with_trims_model import LinearSerializedMagnetWithTrimsModel
from pyaml.magnet.model import MagnetModel
from pyaml.magnet.serialized_magnet_trims import SerializedMagnetsWithTrims
from pyaml.magnet.trim_coil import TrimCoil


@pytest.fixture
def trim_setup():
    # Nonlinear, invertible excitation curve with a nonzero strength offset.
    model = Mock(spec=MagnetModel)
    model.compute_strengths.side_effect = lambda currents: np.asarray(currents) ** 3 + 7.0
    model.compute_hardware_values.side_effect = lambda strengths: np.cbrt(np.asarray(strengths) - 7.0)
    main = Mock(spec=DeviceAccess)
    main.get.return_value = 2.0
    trim = Mock(spec=DeviceAccess)
    trim.get.return_value = 0.5
    trim.get_range.return_value = [-2.0, 2.0]
    trim.name.return_value = "trim/current"
    trim.unit.return_value = "A"
    trim.set.side_effect = lambda value: setattr(trim.get, "return_value", value)
    return model, main, trim


def test_read_trim_strength_tracks_main_current(trim_setup):
    model, main, trim = trim_setup
    strength = RWStrengthTrim(model, main, trim)
    assert strength.get() == pytest.approx(7.625)  # f(2.5) - f(2)

    main.get.return_value = 3.0
    assert strength.get() == pytest.approx(15.875)  # f(3.5) - f(3)
    trim.set.assert_not_called()
    main.set.assert_not_called()


def test_write_trim_strength_with_signed_scaling(trim_setup):
    model, main, trim = trim_setup
    strength = RWStrengthTrim(model, main, trim, trim_factor=-2.0)
    strength.set(19.0)  # f(3) - f(2): equivalent current increases by 1 A.
    trim.set.assert_called_once_with(pytest.approx(-0.5))
    assert strength.get() == pytest.approx(19.0)

    main.get.return_value = 3.0
    strength.set(19.0)
    assert trim.get.return_value == pytest.approx((np.cbrt(46.0) - 3.0) / -2.0)
    assert strength.get() == pytest.approx(19.0)
    main.set.assert_not_called()


def test_out_of_range_rejects_trim_write(trim_setup):
    model, main, trim = trim_setup
    trim.get_range.return_value = [-0.25, 0.25]
    strength = RWStrengthTrim(model, main, trim)
    with pytest.raises(PyAMLException, match="Values out of range"):
        strength.set(19.0)
    main.set.assert_not_called()
    trim.set.assert_not_called()


def test_zero_factor_is_rejected(trim_setup):
    model, main, trim = trim_setup
    with pytest.raises(ValueError, match="nonzero"):
        RWStrengthTrim(model, main, trim, 0.0)


@pytest.fixture
def attached_trim_controls(trim_setup, monkeypatch):
    _, main_device, trim_device = trim_setup
    main_device.get.return_value = 1.0
    main_device.get_range.return_value = [0.0, 3.0]
    main_device.set.side_effect = lambda value: setattr(main_device.get, "return_value", value)
    trim_device.get.return_value = -0.25
    devices = {"main/current": main_device, "trim/current": trim_device}
    controls = ControlSystemAdapter()
    monkeypatch.setattr(controls, "get_device_access", devices.__getitem__)
    model = LinearSerializedMagnetWithTrimsModel(
        curves=InlineCurve([[0, 0], [1, 1], [2, 4], [3, 9]]),
        trims=[TrimCoil("D2", "T2", "trim/current", trim_factor=-2, hardware_unit="trim A")],
        powerconverter="main/current",
        unit="rad",
        hardware_unit="A",
    )
    family = SerializedMagnetsWithTrims("series", "B0", ["D1", "D2"], model)
    model.set_magnet_rigidity(1.0)
    controls.fill_device([family])
    return controls, model, main_device, trim_device


def test_control_attachment_and_independent_trim_supply(attached_trim_controls):
    controls, model, main_device, trim_device = attached_trim_controls
    attached = controls.serialized_magnet["series"]
    trim = controls.magnet["T2"]

    assert isinstance(attached, SerializedMagnetsWithTrims)
    assert attached.names() == ["D1", "D2"]
    assert attached.get_trim_magnets() == [trim]
    assert trim.peer is controls
    assert trim.hardware.unit() == "trim A"
    assert trim.strength.unit() == "rad"
    assert trim.strength.get() == pytest.approx(1.5)

    attached.strength.set(model.compute_mean_strength(2.0))
    np.testing.assert_allclose(attached.hardwares.get(), [2.0, 2.0])
    assert trim.hardware.get() == pytest.approx(-0.25)
    assert trim.strength.get() == pytest.approx(2.5)
    trim_device.set.assert_not_called()

    main_device.set.reset_mock()
    trim.strength.set(1.0)
    assert trim.hardware.get() == pytest.approx(-0.1)
    assert trim.strength.get() == pytest.approx(1.0)
    trim.hardware.set(-0.25)
    assert trim.strength.get() == pytest.approx(2.5)
    main_device.set.assert_not_called()


@pytest.mark.parametrize("use_family", [True, False])
def test_control_array_with_trim_uses_scalar_strengths(attached_trim_controls, monkeypatch, use_family):
    controls, model, main_device, trim_device = attached_trim_controls
    monkeypatch.setattr(controls, "get_aggregator", lambda: Mock(spec=DeviceAccessList))
    family = controls.serialized_magnet["series"]
    trim = controls.magnet["T2"]
    main = family if use_family else family[1]
    magnets = [trim, main]
    assert controls.create_magnet_strength_aggregator(magnets) is None
    assert controls.create_magnet_strength_aggregator([main]) is not None
    assert controls.create_magnet_hardware_aggregator(magnets) is not None
    array = MagnetArray("mixed", magnets)
    main_strength = model.compute_mean_strength(2.0) if use_family else model.compute_strengths([2.0])[1]

    array.strengths.set([1.0, main_strength])

    np.testing.assert_allclose(array.strengths.get(), [1.0, main_strength])
    main_device.set.assert_called_once_with(pytest.approx(2.0))
    trim_device.set.assert_called_once_with(pytest.approx(-0.1))
