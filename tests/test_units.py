"""Tests of the SI unit conversion (issue #350)."""

import numpy as np
import pint
import pytest

from pyaml.accelerator import Accelerator
from pyaml.common.exception import PyAMLConfigException, PyAMLException
from pyaml.common.units import (
    common_unit,
    conversion_factor,
    format_unit,
    get_registry,
    normalize_unit,
    to_magnitude,
    to_quantity,
)

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


@pytest.mark.parametrize("src,dst", [("", "m"), (None, "m"), ("", "1"), ("A", "A"), ("whatever", "whatever")])
def test_conversion_factor_passthrough(src, dst):
    assert conversion_factor(src, dst) == 1.0


@pytest.mark.parametrize(
    "src,dst", [("A", "m"), ("foo", "m"), ("degC", "K"), ("%", "rad"), ("count", "rad"), ("mm", ""), ("Hz", "1")]
)
def test_conversion_factor_errors(src, dst):
    with pytest.raises(PyAMLConfigException):
        conversion_factor(src, dst)


def test_normalize_unit():
    assert normalize_unit(" m-2 ") == "m^-2"
    assert normalize_unit("T.m") == "T*m"
    assert normalize_unit("mm") == "mm"
    # Canonical form reported by unit(): equivalent spellings compare equal
    assert format_unit("m-1") == format_unit("1/m") == format_unit("m^-1") == "1/m"
    assert format_unit("T.m") == "m*T"
    assert format_unit("") == format_unit("No unit") == ""
    assert format_unit("dimensionless") == "1"
    assert format_unit("whatever") == "whatever"


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


def test_to_quantity():
    assert to_quantity(None, "m") is None
    q = to_quantity(1.5, "mm")
    assert q.units == ureg.mm and q.magnitude == 1.5
    assert np.allclose(to_quantity(np.array([1.0, 2.0]), "m").to("mm").magnitude, [1e3, 2e3])
    assert to_quantity(0.2, "").dimensionless
    assert to_quantity(0.2, "1").dimensionless
    assert to_quantity([1.0, 2.0], "m-1").units == 1 / ureg.m  # Accelerator notation
    # Same unit for all values: one array quantity
    q = to_quantity([1.0, 2.0], ["A", "A"])
    assert q.units == ureg.A and np.allclose(q.magnitude, [1.0, 2.0])
    # Mixed units: one quantity per value
    q = to_quantity([0.5, 0.1], ["1/m", "1/m**2"])
    assert isinstance(q, list) and q[0].units == 1 / ureg.m and q[1].units == 1 / ureg.m**2
    with pytest.raises(PyAMLException):
        to_quantity([0.5, 0.1, 0.2], ["1/m", "1/m**2"])
    with pytest.raises(PyAMLException):
        to_quantity(1.0, "foo")


def test_common_unit():
    assert common_unit(["A", "A"]) == "A"
    assert common_unit([["mm", "mm"], ["mm", None]]) == "mm"  # Nested (shaped like get()), missing device ignored
    assert common_unit(["1/m", "1/m**2"]) == ["1/m", "1/m**2"]  # Units that really differ are kept
    assert common_unit([None, None]) is None


def test_any_implementation_accepts_and_returns_quantity():
    from pyaml.common.abstract import ReadFloatArray

    class Positions(ReadFloatArray):  # Minimal read-only interface with a setter, like an external package
        def __init__(self):
            self.value = np.array([1e-3, -2e-3])

        def get(self):
            return self.value

        def set(self, value):
            self.value = value

        def unit(self):
            return "m"

    p = Positions()
    assert not isinstance(p.get(), pint.Quantity)  # Default unchanged
    assert np.allclose(p.get(quantity=True).to("mm").magnitude, [1.0, -2.0])
    p.set(np.array([3.0, 4.0]) * ureg.mm)
    assert np.allclose(p.value, [3e-3, 4e-3])


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


def _quad(name: str, ps: str, unit: str = "1/m") -> dict:
    return {
        "type": "pyaml.magnet.quadrupole",
        "name": name,
        "model": {
            "type": "pyaml.magnet.linear_model",
            "calibration_factor": 0.01,
            "unit": unit,
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
            _quad("Q2", "ps/q2", unit="m-1"),  # Same unit as Q1, spelled differently
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
    bpms = sr.live.diagnostic.bpm.get_array("BPM")
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

    rf.frequency.set(352.372e6)
    assert get_attribute("sr/test/rf/freq") == 352.372  # Divided by the factor: exact, no rounding error
    assert rf.frequency.get() == pytest.approx(352.372e6)
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
def test_quantities_on_control_system(install_test_package):
    from tango.pyaml.attribute_store import get_attribute, set_attribute

    for key, value in [("bpm1/H", 0.1), ("bpm1/V", -0.2), ("bpm2/H", 0.3), ("bpm2/V", -0.4)]:
        set_attribute(f"sr/test/{key}", value, unit="mm")
    sr = Accelerator.from_dict(_config())
    rf = sr.live.rf.get("RF")
    tra = sr.live.rf.transmitter.get("RFTRA")

    # set() converts a quantity to the pyAML unit, then to the device unit
    rf.frequency.set(352.3 * ureg.MHz)
    assert get_attribute("sr/test/rf/freq") == pytest.approx(352.3)
    tra.phase.set(45 * ureg.deg)
    assert get_attribute("sr/test/rf/phase") == pytest.approx(45.0)
    rf.voltage.set(2 * ureg.MV)  # Total voltage, aggregate of transmitters
    assert get_attribute("sr/test/rf/volt") == pytest.approx(2000.0)
    with pytest.raises(PyAMLException):
        rf.frequency.set(1 * ureg.A)

    # get(quantity=True) returns a quantity in unit(), get() still a float
    assert rf.frequency.get(quantity=True).to("MHz").magnitude == pytest.approx(352.3)
    assert isinstance(rf.frequency.get(), float)
    q = sr.live.diagnostic.bpm.get_array("BPM").positions.get(quantity=True)
    assert q.shape == (2, 2) and np.allclose(q.to("mm").magnitude, [[0.1, -0.2], [0.3, -0.4]])

    # Arrays and aggregators
    quads = sr.live.magnet.get_array("QUADS")
    quads.hardwares.set(np.array([1.0, 3.0]) * ureg.A)
    assert [get_attribute("sr/test/ps/q1"), get_attribute("sr/test/ps/q2")] == pytest.approx([1000.0, 3000.0])
    assert np.allclose(quads.hardwares.get(quantity=True).to("mA").magnitude, [1000.0, 3000.0])
    agg = sr.live.create_magnet_strength_aggregator(list(quads))
    agg.set(np.array([0.01, 0.02]) / ureg.m)
    assert [m.strength.get() for m in quads] == pytest.approx([0.01, 0.02])
    assert agg.get(quantity=True).units == 1 / ureg.m


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
    quads = sr.live.magnet.get_array("QUADS")
    strengths = quads.strengths.get()
    assert strengths[0] == pytest.approx(q1.strength.get())
    quads.strengths.set(strengths * 2)
    assert get_attribute("sr/test/ps/q1") == pytest.approx(10000.0)
    assert get_attribute("sr/test/ps/q2") == pytest.approx(14000.0)
    assert np.allclose(quads.hardwares.get(), [10.0, 14.0])


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


def _tune_config(rf_plant_name="RF") -> dict:
    """``_config()`` plus a tune monitor whose devices report the betatron frequency in kHz."""
    cfg = _config()
    cfg["harmonic_number"] = 416
    entries = cfg["controls"][0]["catalog"]["entries"]
    entries += [_entry("tune/h", "kHz", read_only=True), _entry("tune/v", "kHz", read_only=True)]
    monitor = {"type": "pyaml.diagnostics.tune_monitor", "name": "TUNE", "tune_h": "tune/h", "tune_v": "tune/v"}
    if rf_plant_name is not None:
        monitor.update(rf_plant_name=rf_plant_name, tune_above_half=[False, True])
    cfg["devices"].append(monitor)
    return cfg


@TANGO
def test_tune_device_in_frequency_unit(install_test_package):
    from tango.pyaml.attribute_store import set_attribute

    set_attribute("sr/test/tune/h", 180.0, unit="kHz")
    set_attribute("sr/test/tune/v", 300.0, unit="kHz")
    sr = Accelerator.from_dict(_tune_config())
    rf = sr.live.rf.get("RF")
    tune = sr.live.diagnostic.get("TUNE")

    for f_rf in (352.2e6, 352.3e6):  # The revolution frequency follows the RF frequency
        rf.frequency.set(f_rf)
        f_rev = f_rf / 416
        assert rf.revolution_frequency() == pytest.approx(f_rev)
        assert np.allclose(tune.tune.get(), [180e3 / f_rev, 1 - 300e3 / f_rev])  # Vertical tune above half
    # Any betatron sideband (n ± q) f_rev gives the same tune
    for f in (f_rev + 180e3, 2 * f_rev - 180e3):
        set_attribute("sr/test/tune/h", f / 1e3)
        assert tune.tune.get()[0] == pytest.approx(180e3 / f_rev)
    set_attribute("sr/test/tune/h", 180.0)
    assert tune.tune.unit() == "1"
    assert tune.tune.control_system_unit() == "kHz"
    assert tune.frequency.get()[0] == pytest.approx(180e3)

    with pytest.raises(PyAMLConfigException, match="rf_plant_name"):
        Accelerator.from_dict(_tune_config(rf_plant_name=None))


@TANGO
def test_incompatible_device_unit_raises_at_load(install_test_package):
    with pytest.raises(PyAMLConfigException, match="cannot be converted"):
        Accelerator.from_dict(_config(bpm_unit="A"))


@TANGO
@pytest.mark.parametrize("no_unit", ["", "No unit"])
def test_device_without_unit_is_passthrough(install_test_package, no_unit):
    from tango.pyaml.attribute_store import get_attribute

    from pyaml.control.si_deviceaccess import SIDeviceAccess

    sr = Accelerator.from_dict(_config(bpm_unit=no_unit, freq_unit=no_unit, ps_unit=no_unit))
    sr.live.rf.get("RF").frequency.set(352.5)  # Assumed to already be in Hz
    assert get_attribute("sr/test/rf/freq") == pytest.approx(352.5)

    dev = sr.live.get_si_device_access("rf/freq", "Hz")
    assert isinstance(dev, SIDeviceAccess) and dev.factor == 1.0
    assert dev.unit() == "Hz"
    assert dev.control_system_unit() == no_unit

    # Grouped accessors report the SI unit, not the raw device unit
    quads = list(sr.live.magnet.get_array("QUADS"))
    assert sr.live.create_magnet_hardware_aggregator(quads).unit() == "A"
    _, aggh, _ = sr.live.create_bpm_aggregators(list(sr.live.diagnostic.bpm.get_array("BPM")))
    assert aggh.unit() == "m"


@TANGO
def test_accessors_report_control_system_unit(install_test_package):
    from pyaml.control.si_deviceaccess import control_system_unit_of

    sr = Accelerator.from_dict(_config())

    bpm = sr.live.diagnostic.bpm.get("BPM1")
    assert bpm.positions.unit() == "m"
    assert bpm.positions.control_system_unit() == "mm"

    rf = sr.live.rf.get("RF")
    tra = sr.live.rf.transmitter.get("RFTRA")
    assert rf.frequency.control_system_unit() == "MHz"
    assert tra.voltage.control_system_unit() == "kV"
    assert tra.phase.control_system_unit() == "deg"
    assert rf.voltage.control_system_unit() == "V"  # Aggregate of transmitters, no device

    q1 = sr.live.magnet.get("Q1")
    assert q1.hardware.unit() == "A"
    assert q1.hardware.control_system_unit() == "mA"
    assert q1.strength.control_system_unit() == q1.strength.unit()  # No device holds a strength

    quads = sr.live.magnet.get_array("QUADS")
    assert quads.hardwares.control_system_unit() == "mA"
    assert quads.strengths.control_system_unit() == quads.strengths.unit()

    bpms = sr.live.diagnostic.bpm.get_array("BPM")
    assert bpms.positions.control_system_unit() == "mm"
    assert bpms.h.control_system_unit() == "mm"

    # Device level: SIDeviceAccess reports both units, lists one unit per device
    dev = sr.live.get_si_device_access("rf/freq", "Hz")
    assert (dev.unit(), dev.control_system_unit()) == ("Hz", "MHz")
    assert control_system_unit_of(sr.live.get_device_access("rf/freq")) == "MHz"
    assert control_system_unit_of(None) is None
    agg = sr.live.create_magnet_hardware_aggregator(list(quads))
    assert (agg.unit(), agg.control_system_unit()) == ("A", "mA")
    assert agg._devs.control_system_unit() == ["mA", "mA"]


# --------------------------------------------------------------------------- simulator


def test_quantities_on_simulator():
    sr = Accelerator.load("tests/config/EBS_rf.yaml", ignore_external=True)
    freq = sr.design.rf.frequency
    freq.set(352.3 * ureg.MHz)
    assert freq.get() == pytest.approx(352.3e6)
    assert freq.get(quantity=True).to("MHz").magnitude == pytest.approx(352.3)
    assert freq.control_system_unit() == freq.unit() == "Hz"  # No device: same as unit()
    with pytest.raises(PyAMLException):
        freq.set(1 * ureg.m)
    sr.set_energy(6 * ureg.GeV)
    assert sr._energy == pytest.approx(6e9)


def _check_units(acc):
    """A single unit when all values share it, one per value (shaped like get()) only when they differ."""
    values = acc.get()
    for unit in (acc.unit(), acc.control_system_unit()):
        if not isinstance(unit, str):
            assert np.shape(unit) == np.shape(values) and len(set(np.ravel(unit))) > 1, unit
    acc.get(quantity=True)


def test_units_of_simulator_accessors():
    sr = Accelerator.load("tests/config/sr_serialized_magnets.yaml", ignore_external=True)
    series = sr.design.magnet.get_array("QForTune")
    _check_units(series.strengths)
    _check_units(series.hardwares)
    assert series.strengths.unit() == "1/m"  # Declared as m-1, reported in canonical form

    sr = Accelerator.load("tests/config/EBSOrbit.yaml", ignore_external=True)
    bpms = sr.design.diagnostic.bpm.get_array("BPM")
    bpm = sr.design.diagnostic.bpm.get(bpms.names()[0])
    for acc in (bpms.positions, bpms.h, bpms.v, bpm.positions, bpm.offset):
        _check_units(acc)


@TANGO
def test_units_of_control_system_accessors(install_test_package):
    sr = Accelerator.from_dict(_config())
    bpms = sr.live.diagnostic.bpm.get_array("BPM")
    quads = sr.live.magnet.get_array("QUADS")
    assert quads.strengths.unit() == "1/m"  # Q1 in 1/m and Q2 in m-1 share one unit
    accessors = [bpms.positions, bpms.h, bpms.v, quads.hardwares, quads.strengths]
    accessors += [sr.live.create_magnet_strength_aggregator(list(quads))]
    accessors += sr.live.create_bpm_aggregators(list(bpms))
    for acc in accessors:
        _check_units(acc)
