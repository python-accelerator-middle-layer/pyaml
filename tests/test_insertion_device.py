import copy
from unittest.mock import Mock, patch

import at
import numpy as np
import pytest

from pyaml import PyAMLConfigException, PyAMLException
from pyaml.accelerator import Accelerator
from pyaml.common.abstract import ReadWriteFloatScalar
from pyaml.common.element import Element
from pyaml.configuration.factory import Factory
from pyaml.control.abstract_impl import RWScalarBoolean
from pyaml.control.controlsystem import ControlSystem
from pyaml.control.readback_value import Value
from pyaml.insertion_device import InsertionDevice
from pyaml.lattice.simulator import Simulator
from pyaml.validation.validator import SchemaValidator


class _NoHardware(ControlSystem):
    def name(self):
        return "live"

    def get_aggregator(self):
        raise AssertionError("ID metadata attachment must not access hardware")

    def get_device_access(self, ref):
        raise AssertionError("ID metadata attachment must not resolve hardware")


class _Feedforward(Element):
    def _fill_device(self, holder):
        obj = copy.copy(self)
        obj._peer = holder
        holder.add_element(obj)


def _control():
    from tango.pyaml.attribute import Attribute
    from tango.pyaml.attribute import ConfigModel as AttributeConfig
    from tango.pyaml.attribute_store import set_attribute
    from tango.pyaml.catalog import Catalog
    from tango.pyaml.controlsystem import ConfigModel, TangoControlSystem

    set_attribute("GAP", 9.0, unit="mm", range=(2.0, 30.0), readback=8.0)
    set_attribute("MOVING", False)
    set_attribute("MODE", "parallel")
    set_attribute("FF", True)
    catalog = Mock(spec=Catalog)
    catalog.resolve.side_effect = lambda ref: Attribute(AttributeConfig(attribute=ref))
    return TangoControlSystem(ConfigModel(name="live", catalog=catalog))


@pytest.fixture
def id_lattice_file(tmp_path):
    grid = np.linspace(-0.02, 0.02, 4)
    data = {
        "Length": 0.4,
        "xtable": grid,
        "ytable": grid,
        "xkick": np.full((4, 4), 1.0e-4),
        "ykick": np.full((4, 4), -2.0e-4),
        "xkick1": np.zeros((4, 4)),
        "ykick1": np.zeros((4, 4)),
    }
    kickmap = at.InsertionDeviceKickMap("MAP", 1, data, 3.0)
    path = tmp_path / "ids.mat"
    at.save_mat(at.Lattice([kickmap, kickmap.deepcopy(), at.Drift("D", 0.2)], energy=3.0e9), path)
    return str(path)


def _device(**overrides):
    config = {
        "name": "ID",
        "device_id": "SERIAL",
        "control_variables": {"gap": {"unit": "mm", "backend": "GAP", "movement_flag": "MOVING"}},
        "lattice_names": "list(MAP)",
        "model_operating_point": {"gap": 4.0},
    }
    config.update(overrides)
    return InsertionDevice(**config)


def _machine(path, devices=None, controls=None):
    return Accelerator(
        facility="TEST",
        machine="sr",
        energy=3.0e9,
        simulators=[Simulator("design", path), Simulator("comparison", path)],
        controls=[_control()] if controls is None else controls,
        devices=devices or [],
    )


@pytest.mark.parametrize(
    ("declaration", "control_variables", "point"),
    [
        ({"type": "pyaml.insertion_device"}, {"gap": {"unit": "mm"}}, {"gap": 4.0}),
        (
            {"class": "pyaml.insertion_device.InsertionDevice"},
            {"phase": {"unit": "mm"}},
            {"gap": 4.0, "phase": 0.0},
        ),
        (
            {"class_path": "pyaml.insertion_device.insertion_device.InsertionDevice"},
            {"gap": {"unit": "mm"}, "parallel": {"unit": "mm"}, "antiparallel": {"unit": "mm"}},
            {"gap": 4.0, "parallel": 1.0, "antiparallel": 0.0, "mode": "parallel"},
        ),
        (
            {"type": "pyaml.insertion_device"},
            {"ps1": {"unit": "A"}, "ps2": {"unit": "A"}},
            {"ps1": 100.0, "ps2": 0.0},
        ),
    ],
)
def test_configuration_supports_control_variable_families(id_lattice_file, declaration, control_variables, point):
    config = {
        **declaration,
        "name": "ID",
        "device_id": "SERIAL",
        "lattice_names": "list(MAP)",
        "control_variables": control_variables,
        "model_operating_point": point,
    }
    device = Factory.build(SchemaValidator.validate_to_dict(config))
    simulator = Simulator("design", id_lattice_file)
    simulator.fill_device([device])
    attached = simulator.insertion_device.get("ID")
    assert set(attached.control_variables) == set(control_variables)
    for name, definition in control_variables.items():
        assert attached.control_variables[name].get() == point[name]
        assert attached.control_variables[name].unit() == definition["unit"]
    assert attached.model.reference["operating_point"] == point
    assert device.peer is None


@pytest.mark.parametrize(
    ("overrides", "error"),
    [
        ({"control_variables": {}}, "at least one control variable"),
        ({"control_variables": None}, "at least one control variable"),
        ({"control_variables": {"gap": {}}}, "requires a name and unit"),
        ({"control_variables": {"gap": {"unit": "mm", "access": "read"}}}, "expected only unit, backend and movement_flag"),
        ({"control_variables": {"gap": {"unit": "mm", "backend": ""}}}, "backend must not be empty"),
        ({"model_operating_point": {"gap": float("inf")}}, "finite coordinate"),
        ({"model_operating_point": {}}, "include every configured control variable"),
        ({"control_mode": "MODE"}, "include mode"),
        ({"lattice_names": "list(D)"}, "expected InsertionDeviceKickMap"),
        ({"lattice_names": "list(MISSING)"}, "not found in lattice"),
    ],
)
def test_invalid_configuration_or_mapping_is_rejected(id_lattice_file, overrides, error):
    simulator = Simulator("design", id_lattice_file)
    with pytest.raises((PyAMLException, PyAMLConfigException), match=error):
        simulator.fill_device([_device(**overrides)])
    assert not simulator.insertion_device.all()
    assert all(element.PassMethod == "IdTablePass" for element in simulator.ring[:2])


def test_holder_registration_associations_and_add_rollback(id_lattice_file):
    machine = _machine(id_lattice_file)
    machine.add(_Feedforward("ORBIT_FF"))
    machine.add(_Feedforward("TUNE_FF"))
    source = _device(orbit_feedforward="ORBIT_FF", tune_feedforward="TUNE_FF", description="Measured fixed kickmap")
    machine.add(source)
    copies = []
    for holder in machine.modes().values():
        device = holder.insertion_device.get("ID")
        copies.append(device)
        assert holder["ID"] is device
        assert holder.insertion_device.all() == [device]
        assert device.device_id == "SERIAL"
        assert device.orbit_feedforward is holder["ORBIT_FF"]
        assert device.tune_feedforward is holder["TUNE_FF"]
    assert len({id(device) for device in copies}) == len(copies)
    assert source.peer is None
    assert source.orbit_feedforward is None
    with pytest.raises(PyAMLException, match="Duplicate element"):
        machine.add(source)
    with pytest.raises(PyAMLException, match="MISSING"):
        machine.add(_device(name="BAD_ID", orbit_feedforward="MISSING"))
    for holder in machine.modes().values():
        assert "BAD_ID" not in holder._ALL
        assert "BAD_ID" not in holder._INSERTION_DEVICES
    machine.add(_device(name="BAD_ID"))


def test_live_attachment_binds_hardware_separately_from_model(id_lattice_file):
    source = _device(
        control_mode="MODE",
        flags={"moving": "MOVING", "orbit_ff": "FF"},
        model_operating_point={
            "gap": 4.0,
            "mode": "parallel",
        },
    )
    machine = _machine(id_lattice_file, [source])
    live = machine.live.insertion_device.get("ID")
    design = machine.design.insertion_device.get("ID")
    gap = live.control_variables["gap"]
    assert isinstance(gap, ReadWriteFloatScalar)
    assert gap.readback() == 8.0
    assert gap.get() == 9.0
    assert gap.get_range() == [2.0, 30.0]
    assert "phase" not in live.control_variables
    assert isinstance(live.flags["moving"], RWScalarBoolean)
    assert live.flags["moving"].get() is False
    assert live.flags["orbit_ff"].get() is True
    assert live.flag_references["moving"] == "MOVING"
    assert live.control_mode == "MODE"
    assert live.mode.get() == "parallel"
    assert live.model is None
    assert isinstance(design.control_variables["gap"], ReadWriteFloatScalar)
    assert source.control_variables["gap"] is None
    assert source.mode is None
    assert source.flags == {"moving": None, "orbit_ff": None}
    assert design.flags == {"moving": None, "orbit_ff": None}
    assert design.control_variables["gap"].unit() == live.control_variables["gap"].unit() == "mm"
    assert "InsertionDevice" in repr(live)


def test_control_variable_without_backend_remains_unavailable(id_lattice_file):
    machine = _machine(id_lattice_file, [_device(control_variables={"gap": {"unit": "mm"}})], controls=[_NoHardware()])
    live = machine.live.insertion_device.get("ID")
    assert live.control_variables == {"gap": None}
    assert live.flags == {}
    assert live.mode is None
    assert machine.design.insertion_device.get("ID").control_variables["gap"].get() == 4.0


@pytest.mark.parametrize(
    "names",
    [("gap",), ("phase",), ("gap", "parallel", "antiparallel"), ("ps1", "ps2", "ps3")],
)
def test_same_class_binds_mechanical_and_current_control_variables(names):
    from tango.pyaml.attribute_store import set_attribute

    unit = "A" if names[0] == "ps1" else "mm"
    control = _control()
    for name in names:
        set_attribute(name, 0.0, unit=unit, range=(-100.0, 100.0), readback=0.0)
    source = _device(control_variables={name: {"unit": unit, "backend": name} for name in names})
    control.fill_device([source])
    attached = control.insertion_device.get("ID")
    assert type(attached) is InsertionDevice
    assert set(attached.control_variables) == set(names)
    for variable in attached.control_variables.values():
        assert isinstance(variable, ReadWriteFloatScalar)
        variable.set(5.0)
        assert variable.get() == 5.0
        assert variable.readback() == 0.0
        assert variable.unit() == unit
    assert attached.model is None
    assert source.peer is None


def test_writable_and_unavailable_control_variables_are_distinguishable():
    source = _device(
        control_variables={
            "gap": {"unit": "mm", "backend": "GAP"},
            "phase": {"unit": "mm"},
        }
    )
    control = _control()
    control.fill_device([source])
    device = control.insertion_device.get("ID")
    gap = device.control_variables["gap"]
    assert isinstance(gap, ReadWriteFloatScalar)
    assert gap.readback() == 8.0
    assert gap.get() == 9.0
    assert gap.get_range() == [2.0, 30.0]
    assert device.control_variables["phase"] is None
    assert "current" not in device.control_variables


@pytest.mark.parametrize("moving_values", [[], [Value(True), Value(True)]])
def test_set_and_wait_uses_only_boolean_movement_flag(monkeypatch, moving_values):
    control = _control()
    control.fill_device([_device()])
    variable = control.insertion_device.get("ID").control_variables["gap"]
    backend = control.get_device_access("GAP")
    moving = control.get_device_access("MOVING")
    sleep = Mock()
    monkeypatch.setattr("pyaml.control.insertion_device.time.sleep", sleep)
    with (
        patch.object(backend, "set", wraps=backend.set) as write,
        patch.object(backend, "set_and_wait", side_effect=AssertionError("Must not use backend completion logic")),
        patch.object(moving, "readback", side_effect=[*moving_values, Value(False)]),
    ):
        variable.set_and_wait(12.0)
        write.assert_called_once_with(12.0)
    assert sleep.call_count == len(moving_values)
    assert backend.get() == 12.0


def test_set_and_wait_without_flag_does_not_write():
    from tango.pyaml.attribute_store import set_attribute

    set_attribute("CURRENT", 0.0, unit="A", range=(-100.0, 100.0))
    control = _control()
    control.fill_device([_device(control_variables={"current": {"unit": "A", "backend": "CURRENT"}})])
    variable = control.insertion_device.get("ID").control_variables["current"]
    with pytest.raises(PyAMLException, match="requires a movement_flag"):
        variable.set_and_wait(12.0)
    assert variable.get() == 0.0


def test_limits_and_backend_errors_are_propagated():
    control = _control()
    control.fill_device([_device(control_mode="MODE", flags={"ff": "FF"})])
    device = control.insertion_device.get("ID")
    gap = device.control_variables["gap"]
    for method in (gap.set, gap.set_and_wait):
        with pytest.raises(PyAMLException, match="out of range"):
            method(40.0)
    assert gap.get() == 9.0
    for ref, write, value in (
        ("GAP", gap.set_and_wait, 12.0),
        ("MODE", device.mode.set, "antiparallel"),
        ("FF", device.flags["ff"].set, False),
    ):
        error = RuntimeError(f"{ref}: interlocked")
        with patch.object(control.get_device_access(ref), "set", side_effect=error):
            with pytest.raises(RuntimeError) as caught:
                write(value)
        assert caught.value is error
    error = RuntimeError("Cannot read movement flag")
    with patch.object(control.get_device_access("MOVING"), "readback", side_effect=error):
        with pytest.raises(RuntimeError) as caught:
            gap.set_and_wait(12.0)
    assert caught.value is error


def test_unit_mismatch_does_not_register_device():
    control = _control()
    with pytest.raises(PyAMLConfigException, match="does not match"):
        control.fill_device([_device(control_variables={"gap": {"unit": "A", "backend": "GAP"}})])
    assert not control.insertion_device.all()


@pytest.mark.parametrize("value", [False, True, Value(False), Value(True)])
def test_boolean_scalar_reads_boolean_value(value):
    control = _control()
    backend = control.get_device_access("FF")
    with patch.object(backend, "readback", return_value=value):
        assert RWScalarBoolean(backend).get() is bool(value.value if isinstance(value, Value) else value)


def test_boolean_scalar_writes_and_rejects_nonboolean_values():
    control = _control()
    backend = control.get_device_access("FF")
    flag = RWScalarBoolean(backend)
    flag.set(False)
    assert flag.get() is False
    with pytest.raises(PyAMLException, match="boolean flag"):
        flag.set("off")
    with patch.object(backend, "readback", return_value="off"):
        with pytest.raises(PyAMLException, match="boolean flag"):
            flag.get()


def test_optional_controls_and_hardware_motion_do_not_change_model(id_lattice_file):
    from tango.pyaml.attribute_store import set_attribute

    control = _control()
    source = _device(control_mode="MODE", flags={"orbit_ff": "FF"}, model_operating_point={"gap": 4.0, "mode": "parallel"})
    machine = _machine(id_lattice_file, [source], controls=[control])
    live = machine.live.insertion_device.get("ID")
    design = machine.design.insertion_device.get("ID")
    reference = design.model.reference
    live.control_variables["gap"].set_and_wait(12.0)
    set_attribute("GAP", 12.0)
    live.mode.set("antiparallel")
    live.flags["orbit_ff"].set(False)
    assert live.control_variables["gap"].get() == 12.0
    assert live.control_variables["gap"].readback() == 12.0
    assert live.mode.get() == "antiparallel"
    assert live.flags["orbit_ff"].get() is False
    assert design.control_variables["gap"].get() == 4.0
    assert design.control_variables["gap"].get_range() == [4.0, 4.0]
    assert design.model.mode == "parallel"
    with patch.object(control, "get_device_access", side_effect=AssertionError("Model must not access hardware")):
        design.model.disable()
        design.model.enable()
    assert design.model.reference == reference


def test_fixed_reference_rejects_control_variable_writes(id_lattice_file):
    machine = _machine(id_lattice_file, [_device(control_mode="MODE", model_operating_point={"gap": 4.0, "mode": "parallel"})])
    device = machine.design.insertion_device.get("ID")
    variable = device.control_variables["gap"]
    reference = device.model.reference
    assert variable.readback() == variable.get() == 4.0
    for disabled in (False, True):
        if disabled:
            device.model.disable()
        device.model.mode = "parallel"
        for value in (4.0, 5.0, float("nan")):
            for write in (variable.set, variable.set_and_wait):
                with pytest.raises(PyAMLException, match="fixed model operating point"):
                    write(value)
        with pytest.raises(PyAMLException, match="fixed model operating point"):
            device.model.mode = "antiparallel"
        assert variable.get() == 4.0
        assert device.model.reference == reference
    reference["operating_point"]["gap"] = 20.0
    assert device.model.reference["operating_point"]["gap"] == 4.0


def test_model_on_off_preserves_split_maps_and_tracking(id_lattice_file):
    machine = _machine(id_lattice_file, [_device()])
    model = machine.design.insertion_device.get("ID").model
    maps = machine.design.ring[:2]
    original = [(element.PassMethod, element.Length, element.xkick.copy(), element.ykick.copy()) for element in maps]
    reference = model.reference
    particle = np.array([1.0e-3, 0.0, 2.0e-3, 0.0, 0.0, 0.0])
    enabled = at.lattice_track(machine.design.ring, particle.copy(), nturns=1)[0]
    assert model.enabled
    model.disable()
    model.disable()
    assert not model.enabled
    disabled = at.lattice_track(machine.design.ring, particle.copy(), nturns=1)[0]
    drift = at.Lattice([at.Drift("D", sum(element.Length for element in machine.design.ring))], energy=3.0e9)
    np.testing.assert_allclose(disabled, at.lattice_track(drift, particle.copy(), nturns=1)[0])
    assert not np.allclose(disabled, enabled, atol=1e-12, rtol=0)
    assert machine.comparison.insertion_device.get("ID").model.enabled
    assert machine.live.insertion_device.get("ID").model is None
    model.enable()
    model.enable()
    assert model.enabled
    np.testing.assert_allclose(at.lattice_track(machine.design.ring, particle.copy(), nturns=1)[0], enabled)
    for element, (method, length, xkick, ykick) in zip(maps, original, strict=True):
        assert element.PassMethod == method
        assert element.Length == length
        np.testing.assert_array_equal(element.xkick, xkick)
        np.testing.assert_array_equal(element.ykick, ykick)
    assert model.reference == reference
