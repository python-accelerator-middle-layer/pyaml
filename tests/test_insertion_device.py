import copy
from unittest.mock import Mock, patch

import at
import numpy as np
import pytest

from pyaml import PyAMLConfigException, PyAMLException
from pyaml.accelerator import Accelerator
from pyaml.common import abstract
from pyaml.common.abstract_impl import RInsertionDeviceModelPoint
from pyaml.common.element import Element
from pyaml.configuration import NamedValue
from pyaml.configuration.factory import ELEMENT_REGISTRY, Factory
from pyaml.control.abstract_impl import RWBooleanScalar
from pyaml.control.readback_value import Value
from pyaml.insertion_device import ControlVariable, InsertionDevice
from pyaml.lattice.simulator import Simulator
from pyaml.validation.validator import SchemaValidator


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
    if isinstance(config["control_variables"], dict):
        config["control_variables"] = [
            ControlVariable(name=name, **definition) for name, definition in config["control_variables"].items()
        ]
    for field in ("model_operating_point", "disabled_operating_point"):
        if isinstance(config.get(field), dict):
            config[field] = [NamedValue(name=name, value=value) for name, value in config[field].items()]
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
    from tango.pyaml.attribute_store import set_attribute

    control = _control()
    for name, definition in control_variables.items():
        set_attribute(name, 0.0, unit=definition["unit"], range=(-200.0, 200.0), readback=0.0)
    config = {
        **declaration,
        "name": "ID",
        "device_id": "SERIAL",
        "lattice_names": "list(MAP)",
        "control_variables": [
            {"type": "pyaml.insertion_device.control_variable", "name": name, "backend": name, **definition}
            for name, definition in control_variables.items()
        ],
        "model_operating_point": [
            {"type": "pyaml.configuration.named_value", "name": name, "value": value} for name, value in point.items()
        ],
        "disabled_operating_point": [
            {"type": "pyaml.configuration.named_value", "name": name, "value": 0.0} for name in control_variables
        ],
    }
    device = Factory.build(SchemaValidator.validate_to_dict(config))
    simulator = Simulator("design", id_lattice_file)
    simulator.fill_device([device])
    control.fill_device([device])
    attached = simulator.insertion_device.get("ID")
    live = control.insertion_device.get("ID")
    assert set(attached.control_variables) == set(control_variables)
    assert set(live.control_variables) == set(control_variables)
    for name, definition in control_variables.items():
        assert attached.control_variables[name].get() == point[name]
        assert attached.control_variables[name].unit() == definition["unit"]
        variable = live.control_variables[name]
        variable.set(5.0)
        assert variable.get() == 5.0
        assert variable.readback() == 0.0
        assert variable.unit() == definition["unit"]
    assert live.mode is None
    assert live.flags == {}
    assert attached.model_reference["operating_point"] == point
    assert attached.disabled_operating_point == {name: 0.0 for name in control_variables}
    assert device.peer is None
    assert "gap" not in ELEMENT_REGISTRY
    assert "phase" not in ELEMENT_REGISTRY


@pytest.mark.parametrize(
    ("overrides", "error"),
    [
        ({"control_variables": {}}, "at least one control variable"),
        ({"control_variables": {"gap": {"unit": ""}}}, "requires a name and unit"),
        ({"control_variables": {"gap": {"unit": "mm", "backend": ""}}}, "backend must not be empty"),
        ({"model_operating_point": {"gap": float("inf")}}, "finite coordinate"),
        ({"disabled_operating_point": {"missing": 0.0}}, "requires a configured control variable"),
        ({"disabled_operating_point": {"gap": float("nan")}}, "finite setpoint"),
        ({"disabled_operating_point": {"gap": True}}, "finite setpoint"),
        ({"model_operating_point": {"gap": True}}, "finite coordinate"),
        ({"model_operating_point": {"gap": "4.0"}}, "finite coordinate"),
        ({"model_operating_point": {"gap": 4.0, "mode": 1.0}}, "string mode"),
        (
            {"control_variables": [ControlVariable("gap", "mm"), ControlVariable("gap", "mm")]},
            "duplicate names in control_variables",
        ),
        (
            {"model_operating_point": [NamedValue("gap", 4.0), NamedValue("gap", 5.0)]},
            "duplicate names in model_operating_point",
        ),
    ],
)
def test_invalid_configuration_is_rejected(overrides, error):
    with pytest.raises(PyAMLConfigException, match=error):
        _device(**overrides)


@pytest.mark.parametrize(
    ("overrides", "error"),
    [
        ({"model_operating_point": {}}, "include every configured control variable"),
        ({"control_mode": "MODE"}, "include mode"),
        ({"lattice_names": "list(D)"}, "expected InsertionDeviceKickMap"),
    ],
)
def test_invalid_model_binding_does_not_register_device(id_lattice_file, overrides, error):
    simulator = Simulator("design", id_lattice_file)
    with pytest.raises(PyAMLException, match=error):
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
        assert type(device) is InsertionDevice
        assert isinstance(device.enabled, abstract.RWBooleanScalar)
        copies.append(device)
        assert holder["ID"] is device
        assert holder.insertion_device.all() == [device]
        assert device.device_id == "SERIAL"
        assert device.orbit_feedforward is holder["ORBIT_FF"]
        assert device.tune_feedforward is holder["TUNE_FF"]
    assert len({id(device) for device in copies}) == len(copies)
    assert source.peer is None
    assert source.orbit_feedforward is None
    with pytest.raises(PyAMLException, match="MISSING"):
        machine.add(_device(name="BAD_ID", orbit_feedforward="MISSING"))
    for holder in machine.modes().values():
        assert "BAD_ID" not in holder._ALL
        assert "BAD_ID" not in holder._INSERTION_DEVICES
    machine.add(_device(name="BAD_ID"))


def test_live_attachment_binds_hardware_separately_from_model(id_lattice_file):
    from tango.pyaml.attribute_store import set_attribute

    control = _control()
    source = _device(
        control_variables={
            "gap": {"unit": "mm", "backend": "GAP", "movement_flag": "MOVING"},
            "phase": {"unit": "mm"},
        },
        control_mode="MODE",
        flags={"moving": "MOVING", "orbit_ff": "FF"},
        model_operating_point={
            "gap": 4.0,
            "phase": 0.0,
            "mode": "parallel",
        },
    )
    with (
        patch.object(control, "get_device_access", wraps=control.get_device_access) as lookup,
        patch.object(control, "get_aggregator", side_effect=AssertionError("ID must not create hardware aggregators")),
    ):
        machine = _machine(id_lattice_file, [source], controls=[control])
    assert {args[0] for args, _ in lookup.call_args_list} == {"GAP", "MOVING", "FF", "MODE"}
    live = machine.live.insertion_device.get("ID")
    design = machine.design.insertion_device.get("ID")
    gap = live.control_variables["gap"]
    assert isinstance(gap, abstract.ReadWriteFloatScalar)
    assert gap.readback() == 8.0
    assert gap.get() == 9.0
    assert gap.get_range() == [2.0, 30.0]
    assert live.control_variables["phase"] is None
    assert "current" not in live.control_variables
    assert isinstance(live.flags["moving"], RWBooleanScalar)
    assert live.flags["moving"].get() is False
    assert live.flags["orbit_ff"].get() is True
    assert live.mode.get() == "parallel"
    assert design.flags == {"moving": None, "orbit_ff": None}
    point = live.model_operating_point
    assert isinstance(point, RInsertionDeviceModelPoint)
    assert point is design.model_operating_point is source.model_operating_point
    assert dict(point) == {"gap": 4.0, "phase": 0.0, "mode": "parallel"}
    assert point.units == {"gap": "mm", "phase": "mm"}
    with pytest.raises(TypeError):
        point["gap"] = 20.0
    with pytest.raises(TypeError):
        point.units["gap"] = "m"
    assert design.control_variables["gap"].unit() == live.control_variables["gap"].unit() == "mm"
    reference = design.model_reference
    gap.set_and_wait(12.0)
    set_attribute("GAP", 12.0)
    live.mode.set("antiparallel")
    live.flags["orbit_ff"].set(False)
    assert gap.get() == gap.readback() == 12.0
    assert live.mode.get() == "antiparallel"
    assert live.flags["orbit_ff"].get() is False
    assert design.control_variables["gap"].get() == 4.0
    assert design.control_variables["phase"].get() == 0.0
    assert design.mode.get() == "parallel"
    with patch.object(control, "get_device_access", side_effect=AssertionError("Model must not access hardware")):
        design.disable()
        design.enable()
    assert design.model_reference == reference
    assert dict(point) == reference["operating_point"]


@pytest.mark.parametrize("moving_values", [[], [Value(True), Value(True)]])
def test_set_and_wait_uses_only_boolean_movement_flag(monkeypatch, moving_values):
    control = _control()
    control.fill_device([_device()])
    variable = control.insertion_device.get("ID").control_variables["gap"]
    backend = control.get_device_access("GAP")
    moving = control.get_device_access("MOVING")
    sleep = Mock()
    monkeypatch.setattr("pyaml.control.abstract_impl.time.sleep", sleep)
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


def test_boolean_scalar_reads_writes_and_rejects_nonboolean_values():
    control = _control()
    backend = control.get_device_access("FF")
    flag = RWBooleanScalar(backend)
    flag.set(False)
    assert flag.get() is False
    with patch.object(backend, "readback", return_value=True):
        assert flag.get() is True
    with pytest.raises(PyAMLException, match="boolean flag"):
        flag.set("off")
    with patch.object(backend, "readback", return_value="off"):
        with pytest.raises(PyAMLException, match="boolean flag"):
            flag.get()


def test_fixed_reference_rejects_control_variable_writes(id_lattice_file):
    machine = _machine(id_lattice_file, [_device(control_mode="MODE", model_operating_point={"gap": 4.0, "mode": "parallel"})])
    device = machine.design.insertion_device.get("ID")
    variable = device.control_variables["gap"]
    reference = device.model_reference
    assert variable.readback() == variable.get() == 4.0
    assert variable.get_range() == [4.0, 4.0]
    for disabled in (False, True):
        if disabled:
            device.disable()
        device.mode.set("parallel")
        for value in (4.0, 5.0, float("nan")):
            for write in (variable.set, variable.set_and_wait):
                with pytest.raises(PyAMLException, match="fixed model operating point"):
                    write(value)
        with pytest.raises(PyAMLException, match="fixed model operating point"):
            device.mode.set("antiparallel")
        assert variable.get() == 4.0
        assert device.model_reference == reference
    reference["operating_point"]["gap"] = 20.0
    assert device.model_reference["operating_point"]["gap"] == 4.0


def test_model_on_off_preserves_split_maps_and_tracking(id_lattice_file):
    machine = _machine(id_lattice_file, [_device()])
    device = machine.design.insertion_device.get("ID")
    maps = machine.design.ring[:2]
    original = [(element.PassMethod, element.Length, element.xkick.copy(), element.ykick.copy()) for element in maps]
    reference = device.model_reference
    assert reference["maps"] == tuple(getattr(element, "Filename_in", None) for element in maps)
    particle = np.array([1.0e-3, 0.0, 2.0e-3, 0.0, 0.0, 0.0])
    enabled = at.lattice_track(machine.design.ring, particle.copy(), nturns=1)[0]
    with pytest.raises(PyAMLException, match="boolean enabled state"):
        device.enabled.set(1)
    assert device.enabled.get()
    device.disable()
    device.enabled.set(False)
    assert not device.enabled.get()
    disabled = at.lattice_track(machine.design.ring, particle.copy(), nturns=1)[0]
    drift = at.Lattice([at.Drift("D", sum(element.Length for element in machine.design.ring))], energy=3.0e9)
    np.testing.assert_allclose(disabled, at.lattice_track(drift, particle.copy(), nturns=1)[0])
    assert not np.allclose(disabled, enabled, atol=1e-12, rtol=0)
    assert machine.comparison.insertion_device.get("ID").enabled.get()
    assert machine.live.insertion_device.get("ID").enabled.get()
    device.enable()
    device.enabled.set(True)
    assert device.enabled.get()
    np.testing.assert_allclose(at.lattice_track(machine.design.ring, particle.copy(), nturns=1)[0], enabled)
    for element, (method, length, xkick, ykick) in zip(maps, original, strict=True):
        assert element.PassMethod == method
        assert element.Length == length
        np.testing.assert_array_equal(element.xkick, xkick)
        np.testing.assert_array_equal(element.ykick, ykick)
    assert device.model_reference == reference


def test_live_enable_disable_apply_points_and_keep_logical_state():
    control = _control()
    control.fill_device(
        [
            _device(
                control_mode="MODE",
                model_operating_point={"gap": 4.0, "mode": "parallel"},
                disabled_operating_point={"gap": 30},
            )
        ]
    )
    device = control.insertion_device.get("ID")
    reference = device.model_reference
    gap = device.control_variables["gap"]
    assert device.enabled.get() is True
    with pytest.raises(PyAMLException, match="boolean enabled state"):
        device.enabled.set(1)
    assert device.enabled.get() is True
    gap.set(30.0)
    assert device.enabled.get() is True
    device.mode.set("antiparallel")
    with patch.object(control.get_device_access("MOVING"), "readback", side_effect=AssertionError("Must not wait")):
        device.enable()
        assert gap.get() == 4.0
        assert device.mode.get() == "parallel"
        gap.set(12.0)
        device.enabled.set(True)
        assert gap.get() == 4.0
        device.disable()
        assert device.enabled.get() is False
        assert gap.get() == 30.0
        gap.set(12.0)
        assert device.enabled.get() is False
        device.enabled.set(False)
        assert gap.get() == 30.0
    assert gap.readback() == 8.0
    assert device.model_reference == reference


@pytest.mark.parametrize(("values", "enabled"), [((0.0, 0.0), False), ((1.0e-12, 0.0), True), ((0.0, 1.0), True)])
def test_initial_live_state_matches_all_disabled_requested_setpoints(values, enabled):
    from tango.pyaml.attribute_store import set_attribute

    control = _control()
    names = ("ps1", "ps2")
    for name, value in zip(names, values, strict=True):
        set_attribute(name, value, unit="A", range=(-100.0, 100.0), readback=50.0)
    control.fill_device(
        [
            _device(
                control_variables={name: {"unit": "A", "backend": name} for name in names},
                model_operating_point={"ps1": 10.0, "ps2": 20.0},
                disabled_operating_point={name: 0.0 for name in names},
            )
        ]
    )
    device = control.insertion_device.get("ID")
    assert device.enabled.get() is enabled
    device.enable()
    assert [device.control_variables[name].get() for name in names] == [10.0, 20.0]
    device.disable()
    assert [device.control_variables[name].get() for name in names] == [0.0, 0.0]


@pytest.mark.parametrize(
    ("overrides", "command", "error"),
    [
        ({}, "disable", "disabled_operating_point is required"),
        ({"model_operating_point": None}, "enable", "include every configured control variable"),
        ({"control_mode": "MODE"}, "enable", "include mode"),
        ({"control_variables": {"gap": {"unit": "mm"}}}, "enable", "control variable is unavailable"),
    ],
)
def test_live_enable_disable_missing_configuration_fails_before_writes(overrides, command, error):
    control = _control()
    control.fill_device([_device(**overrides)])
    device = control.insertion_device.get("ID")
    backend = control.get_device_access("GAP")
    with patch.object(backend, "set", wraps=backend.set) as write:
        with pytest.raises(PyAMLException, match=error):
            getattr(device, command)()
        write.assert_not_called()
    assert device.enabled.get() is True


def test_live_enable_prevalidates_all_targets_before_writing():
    from tango.pyaml.attribute_store import set_attribute

    control = _control()
    set_attribute("PHASE", 0.0, unit="mm", range=(-10.0, 10.0))
    control.fill_device(
        [
            _device(
                control_variables={"gap": {"unit": "mm", "backend": "GAP"}, "phase": {"unit": "mm", "backend": "PHASE"}},
                model_operating_point={"gap": 4.0, "phase": 20.0},
                disabled_operating_point={"gap": 30.0},
            )
        ]
    )
    device = control.insertion_device.get("ID")
    backend = control.get_device_access("GAP")
    with patch.object(backend, "set", wraps=backend.set) as write:
        with pytest.raises(PyAMLException, match="out of range"):
            device.enable()
        write.assert_not_called()
    device.disable()
    assert device.control_variables["gap"].get() == 30.0
    assert device.control_variables["phase"].get() == 0.0


@pytest.mark.parametrize(("command", "ref"), [("disable", "GAP"), ("enable", "MODE")])
def test_live_enable_disable_failures_do_not_update_logical_state(command, ref):
    control = _control()
    control.fill_device(
        [
            _device(
                control_mode="MODE",
                model_operating_point={"gap": 4.0, "mode": "parallel"},
                disabled_operating_point={"gap": 30.0},
            )
        ]
    )
    device = control.insertion_device.get("ID")
    if command == "enable":
        device.disable()
    previous = device.enabled.get()
    error = RuntimeError("Interlocked")
    with patch.object(control.get_device_access(ref), "set", side_effect=error):
        with pytest.raises(RuntimeError) as caught:
            getattr(device, command)()
    assert caught.value is error
    assert device.enabled.get() is previous
    if command == "enable":
        assert device.control_variables["gap"].get() == 4.0


@pytest.mark.parametrize("disabled_maps", [1, 2])
def test_design_initial_enabled_state_comes_from_consistent_kickmaps(id_lattice_file, disabled_maps):
    simulator = Simulator("design", id_lattice_file)
    for element in simulator.ring[:disabled_maps]:
        element.disable()
    if disabled_maps == 1:
        with pytest.raises(PyAMLException, match="inconsistent kickmap enabled states"):
            simulator.fill_device([_device()])
        assert not simulator.insertion_device.all()
    else:
        simulator.fill_device([_device()])
        device = simulator.insertion_device.get("ID")
        assert device.enabled.get() is False
        device.enable()
        assert device.enabled.get() is True
        assert all(element.PassMethod == "IdTablePass" for element in simulator.ring[:2])
