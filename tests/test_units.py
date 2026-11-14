"""Tests of the SI unit conversion (issue #350)."""

import numpy as np
import pint
import pytest

from pyaml.accelerator import Accelerator
from pyaml.common.exception import PyAMLConfigException, PyAMLException
from pyaml.common.units import conversion_factor, get_registry, normalize_unit, to_magnitude

TANGO = pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)

ureg = get_registry()


# --------------------------------------------------------------------------- units module


@pytest.mark.parametrize(
    "src,dst,k",
    [
        ("nm", "m", 1e-9),
        ("mm", "m", 1e-3),
        ("MHz", "Hz", 1e6),
        ("kV", "V", 1e3),
        ("mrad", "rad", 1e-3),
        ("deg", "rad", np.pi / 180),
        ("mA", "A", 1e-3),
        ("m-1", "1/m", 1.0),
        ("T.m", "T*m", 1.0),
    ],
)
def test_conversion_factor(src, dst, k):
    assert conversion_factor(src, dst) == pytest.approx(k)


@pytest.mark.parametrize("src,dst", [("", "m"), (None, "m"), ("mm", ""), ("A", "A"), ("whatever", "whatever")])
def test_conversion_factor_passthrough(src, dst):
    assert conversion_factor(src, dst) == 1.0


@pytest.mark.parametrize("src,dst", [("A", "m"), ("foo", "m"), ("degC", "K"), ("%", "rad"), ("count", "rad")])
def test_conversion_factor_errors(src, dst):
    with pytest.raises(PyAMLConfigException):
        conversion_factor(src, dst)


def test_normalize_unit():
    assert normalize_unit(" m-2 ") == "m^-2"
    assert normalize_unit("T.m") == "T*m"
    assert normalize_unit("mm") == "mm"


def test_to_magnitude():
    assert to_magnitude(1.5, "m") == 1.5
    assert to_magnitude(3 * ureg.mm, "m") == pytest.approx(3e-3)
    assert np.allclose(to_magnitude(np.array([1.0, 2.0]) * ureg.mm, "m"), [1e-3, 2e-3])
    assert np.allclose(to_magnitude([1 * ureg.mm, 2 * ureg.um], ["m", "m"]), [1e-3, 2e-6])
    assert to_magnitude(0.2 * ureg.dimensionless, "1") == pytest.approx(0.2)
    # A quantity from another registry is accepted too
    assert to_magnitude(pint.UnitRegistry().Quantity(352, "MHz"), "Hz") == pytest.approx(352e6)
    with pytest.raises(PyAMLException):
        to_magnitude(1 * ureg.A, "Hz")


def test_to_magnitude_scalar_quantity_broadcast_to_unit_list():
    assert np.allclose(to_magnitude(2 * ureg.mm, ["m", "km"]), [2e-3, 2e-6])
    with pytest.raises(PyAMLException):
        to_magnitude(0.5 / ureg.m, ["1/m", "1/m**2"])


def test_read_write_interfaces_accept_quantity():
    from pyaml.common.abstract import ReadFloatScalar

    class Tilt(ReadFloatScalar):  # Read-only interface with a setter, like the BPM tilt
        def __init__(self):
            self.value = 0.0

        def get(self):
            return self.value

        def set(self, value):
            self.value = value

        def unit(self):
            return "rad"

    t = Tilt()
    t.set(1 * ureg.mrad)
    assert t.value == pytest.approx(1e-3)


def test_hardware_unit_of_model():
    from pyaml.control.controlsystem import _hardware_unit

    class Model:
        def __init__(self, units):
            self.units = units

        def get_hardware_units(self):
            return self.units

    assert _hardware_unit(Model(["A"]), 2) == "A"  # One unit shared by all devices
    assert _hardware_unit(Model(["A", "mA"]), 1) == "mA"
    assert _hardware_unit(Model([None]), 0) == ""
    with pytest.raises(PyAMLConfigException):
        _hardware_unit(Model(["A", "A"]), 2)


# --------------------------------------------------------------------------- control system


def _entry(key: str, unit: str, range=None, read_only=False) -> dict:
    device = {
        "type": "tango.pyaml.attribute_read_only" if read_only else "tango.pyaml.attribute",
        "attribute": f"sr/test/{key}",
        "unit": unit,
    }
    if range is not None:
        device["range"] = range
    return {"type": "tango.pyaml.static_catalog_entry", "key": key, "device": device}


def _quad(name: str, ps: str) -> dict:
    return {
        "type": "pyaml.magnet.quadrupole",
        "name": name,
        "model": {
            "type": "pyaml.magnet.linear_model",
            "calibration_factor": 0.01,
            "unit": "1/m",
            "hardware_unit": "A",
            "powerconverter": ps,
        },
    }


def _config(bpm_unit="mm", freq_unit="MHz", volt_unit="kV", phase_unit="deg", ps_unit="mA") -> dict:
    entries = [
        _entry("bpm1/H", bpm_unit, read_only=True),
        _entry("bpm1/V", bpm_unit, read_only=True),
        _entry("bpm2/H", bpm_unit, read_only=True),
        _entry("bpm2/V", bpm_unit, read_only=True),
        _entry("rf/freq", freq_unit, range=[352.0, 353.0]),
        _entry("rf/volt", volt_unit),
        _entry("rf/phase", phase_unit),
        _entry("ps/q1", ps_unit),
        _entry("ps/q2", ps_unit),
    ]
    return {
        "type": "pyaml.accelerator",
        "facility": "ESRF",
        "machine": "sr",
        "energy": 6e9,
        "data_folder": "/data/store",
        "controls": [
            {
                "type": "tango.pyaml.controlsystem",
                "tango_host": "ebs-simu-3:10000",
                "name": "live",
                "catalog": {"type": "tango.pyaml.static_catalog", "entries": entries},
            }
        ],
        "arrays": [
            {"type": "pyaml.arrays.bpm", "name": "BPM", "elements": ["BPM1", "BPM2"]},
            {"type": "pyaml.arrays.magnet", "name": "QUADS", "elements": ["Q1", "Q2"]},
        ],
        "devices": [
            {"type": "pyaml.diagnostics.bpm.bpm", "name": "BPM1", "x_pos": "bpm1/H", "y_pos": "bpm1/V"},
            {"type": "pyaml.diagnostics.bpm.bpm", "name": "BPM2", "x_pos": "bpm2/H", "y_pos": "bpm2/V"},
            {
                "type": "pyaml.rf.rf_plant",
                "name": "RF",
                "masterclock": "rf/freq",
                "transmitters": [
                    {
                        "type": "pyaml.rf.rf_transmitter",
                        "name": "RFTRA",
                        "cavities": ["CAV1"],
                        "voltage": "rf/volt",
                        "phase": "rf/phase",
                    }
                ],
            },
            _quad("Q1", "ps/q1"),
            _quad("Q2", "ps/q2"),
        ],
    }


@TANGO
def test_bpm_positions_are_converted_to_si(install_test_package):
    from tango.pyaml.attribute_store import get_attribute, set_attribute

    for key, value in [("bpm1/H", 0.1), ("bpm1/V", -0.2), ("bpm2/H", 0.3), ("bpm2/V", -0.4)]:
        set_attribute(f"sr/test/{key}", value, unit="mm")
    sr = Accelerator.from_dict(_config())

    bpm = sr.live.diagnostic.bpm.get("BPM1")
    assert np.allclose(bpm.positions.get(), [0.1e-3, -0.2e-3])
    assert bpm.positions.unit() == "m"

    # The grouped read gives the same values as the per-element reads
    bpms = sr.live.diagnostic.bpms.get("BPM")
    assert np.allclose(bpms.positions.get(), [[0.1e-3, -0.2e-3], [0.3e-3, -0.4e-3]])
    assert np.allclose(bpms.h.get(), [0.1e-3, 0.3e-3])
    assert np.allclose(bpms.v.get(), [-0.2e-3, -0.4e-3])

    # The raw control-system value is untouched
    assert get_attribute("sr/test/bpm1/H") == pytest.approx(0.1)


@TANGO
def test_rf_is_converted_to_si(install_test_package):
    from tango.pyaml.attribute_store import get_attribute

    sr = Accelerator.from_dict(_config())
    rf = sr.live.rf.get("RF")
    tra = sr.live.rf.transmitter.get("RFTRA")

    rf.frequency.set(352.2e6)
    assert get_attribute("sr/test/rf/freq") == pytest.approx(352.2)
    assert rf.frequency.get() == pytest.approx(352.2e6)
    assert rf.frequency.unit() == "Hz"

    tra.voltage.set(1.5e6)
    assert get_attribute("sr/test/rf/volt") == pytest.approx(1500.0)
    assert tra.voltage.get() == pytest.approx(1.5e6)
    assert tra.voltage.unit() == "V"

    tra.phase.set(np.pi / 2)
    assert get_attribute("sr/test/rf/phase") == pytest.approx(90.0)
    assert tra.phase.get() == pytest.approx(np.pi / 2)
    assert tra.phase.unit() == "rad"


@TANGO
def test_set_accepts_quantity_on_control_system(install_test_package):
    from tango.pyaml.attribute_store import get_attribute

    sr = Accelerator.from_dict(_config())
    rf = sr.live.rf.get("RF")
    tra = sr.live.rf.transmitter.get("RFTRA")

    rf.frequency.set(352.3 * ureg.MHz)
    assert get_attribute("sr/test/rf/freq") == pytest.approx(352.3)
    tra.voltage.set(0.8 * ureg.MV)
    assert get_attribute("sr/test/rf/volt") == pytest.approx(800.0)
    tra.phase.set(45 * ureg.deg)
    assert get_attribute("sr/test/rf/phase") == pytest.approx(45.0)

    q1 = sr.live.magnet.get("Q1")
    q1.hardware.set(2 * ureg.A)
    assert get_attribute("sr/test/ps/q1") == pytest.approx(2000.0)

    # Arrays and aggregators accept quantities too
    quads = sr.live.magnets.get("QUADS")
    quads.hardwares.set(np.array([1.0, 3.0]) * ureg.A)
    assert get_attribute("sr/test/ps/q1") == pytest.approx(1000.0)
    assert get_attribute("sr/test/ps/q2") == pytest.approx(3000.0)

    with pytest.raises(PyAMLException):
        rf.frequency.set(1 * ureg.A)


@TANGO
def test_range_is_converted_to_si(install_test_package):
    sr = Accelerator.from_dict(_config())
    rf = sr.live.rf.get("RF")
    rf.frequency.set(352.5e6)  # Within [352, 353] MHz
    dev_range = sr.live.get_si_device_access("rf/freq", "Hz").get_range()
    assert np.allclose(dev_range, [352e6, 353e6])


@TANGO
def test_magnet_device_unit_is_converted_to_model_hardware_unit(install_test_package):
    from tango.pyaml.attribute_store import get_attribute, set_attribute

    set_attribute("sr/test/ps/q1", 5000.0, unit="mA")
    set_attribute("sr/test/ps/q2", 7000.0, unit="mA")
    sr = Accelerator.from_dict(_config())

    q1 = sr.live.magnet.get("Q1")
    assert q1.hardware.get() == pytest.approx(5.0)
    assert q1.hardware.unit() == "A"

    # Strength computed from the current in A, same result as a device declared in A
    sr_a = Accelerator.from_dict(_config(ps_unit="A"))
    set_attribute("sr/test/ps/q1", 5.0)
    assert q1.strength.get() == pytest.approx(sr_a.live.magnet.get("Q1").strength.get())
    set_attribute("sr/test/ps/q1", 5000.0)

    # Strength aggregator (grouped access) is consistent with element access
    quads = sr.live.magnets.get("QUADS")
    strengths = quads.strengths.get()
    assert strengths[0] == pytest.approx(q1.strength.get())
    quads.strengths.set(strengths * 2)
    assert get_attribute("sr/test/ps/q1") == pytest.approx(10000.0)
    assert get_attribute("sr/test/ps/q2") == pytest.approx(14000.0)
    assert np.allclose(quads.hardwares.get(), [10.0, 14.0])


@TANGO
def test_strength_aggregator_unit_and_quantity(install_test_package):
    from tango.pyaml.attribute_store import get_attribute

    sr = Accelerator.from_dict(_config())
    agg = sr.live.create_magnet_strength_aggregator(list(sr.live.magnets.get("QUADS")))
    assert agg.unit() == ["1/m", "1/m"]
    agg.set(np.array([0.01, 0.02]) / ureg.m)
    q1, q2 = sr.live.magnet.get("Q1"), sr.live.magnet.get("Q2")
    assert [q1.strength.get(), q2.strength.get()] == pytest.approx([0.01, 0.02])
    assert get_attribute("sr/test/ps/q1") == pytest.approx(1000 * q1.hardware.get())


@TANGO
def test_device_unit_error_is_not_swallowed(install_test_package):
    from pyaml.control.si_deviceaccess import wrap_si

    sr = Accelerator.from_dict(_config())
    dev = sr.live.get_device_access("bpm1/H")

    def broken_unit():
        raise RuntimeError("device offline")

    dev.unit = broken_unit
    with pytest.raises(RuntimeError, match="device offline"):
        wrap_si(dev, "m")


@TANGO
def test_incompatible_device_unit_raises_at_load(install_test_package):
    with pytest.raises(PyAMLConfigException, match="cannot be converted"):
        Accelerator.from_dict(_config(bpm_unit="A"))


@TANGO
def test_device_without_unit_is_passthrough(install_test_package):
    from tango.pyaml.attribute_store import get_attribute

    sr = Accelerator.from_dict(_config(freq_unit=""))
    sr.live.rf.get("RF").frequency.set(352.5)
    assert get_attribute("sr/test/rf/freq") == pytest.approx(352.5)


# --------------------------------------------------------------------------- simulator


def test_set_accepts_quantity_on_simulator():
    sr = Accelerator.load("tests/config/EBS_rf.yaml", ignore_external=True)
    sr.design.rf.frequency.set(352.3 * ureg.MHz)
    assert sr.design.rf.frequency.get() == pytest.approx(352.3e6)
    with pytest.raises(PyAMLException):
        sr.design.rf.frequency.set(1 * ureg.m)


def test_set_energy_accepts_quantity():
    sr = Accelerator.load("tests/config/EBS_rf.yaml", ignore_external=True)
    sr.set_energy(6 * ureg.GeV)
    assert sr._energy == pytest.approx(6e9)
