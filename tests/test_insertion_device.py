import copy

import at
import numpy as np
import pytest

from pyaml import PyAMLConfigException, PyAMLException
from pyaml.accelerator import Accelerator
from pyaml.common.abstract import ReadFloatScalar, ReadWriteFloatScalar
from pyaml.common.element import Element
from pyaml.configuration.factory import Factory
from pyaml.control.controlsystem import ControlSystem
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
        "drives": {"gap": {"unit": "mm", "backend": "GAP", "movement_flag": "MOVING"}},
        "lattice_names": "list(MAP)",
        "model_operating_point": {"gap": 4.0},
    }
    config.update(overrides)
    return InsertionDevice(**config)


def _machine(path, devices=None):
    return Accelerator(
        facility="TEST",
        machine="sr",
        energy=3.0e9,
        simulators=[Simulator("design", path), Simulator("comparison", path)],
        controls=[_NoHardware()],
        devices=devices or [],
    )


@pytest.mark.parametrize(
    ("declaration", "drives", "point"),
    [
        ({"type": "pyaml.insertion_device"}, {"gap": {"unit": "mm"}}, {"gap": 4.0}),
        ({"class": "pyaml.insertion_device.InsertionDevice"}, {"phase": {"unit": "mm"}}, {"gap": 4.0, "phase": 0.0}),
        (
            {"class_path": "pyaml.insertion_device.InsertionDevice"},
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
def test_configuration_supports_optional_drive_families(id_lattice_file, declaration, drives, point):
    config = {
        **declaration,
        "name": "ID",
        "device_id": "SERIAL",
        "lattice_names": "list(MAP)",
        "drives": drives,
        "model_operating_point": point,
    }
    device = Factory.build(SchemaValidator.validate_to_dict(config))
    simulator = Simulator("design", id_lattice_file)
    simulator.fill_device([device])
    attached = simulator.insertion_device.get("ID")
    assert set(attached.components) == set(drives)
    for name, definition in drives.items():
        assert attached.components[name].get() == point[name]
        assert attached.components[name].unit() == definition["unit"]
    assert attached.model.reference["operating_point"] == point
    assert device.peer is None


@pytest.mark.parametrize(
    ("overrides", "error"),
    [
        ({"drives": {"gap": {}}}, "requires a name and unit"),
        ({"model_operating_point": {"gap": float("inf")}}, "finite coordinate"),
        ({"model_operating_point": {}}, "include every configured drive"),
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


def test_live_attachment_has_no_simulated_hardware_values(id_lattice_file):
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
    assert live.components["gap"] is None
    assert "phase" not in live.components
    assert live.flags == {"moving": None, "orbit_ff": None}
    assert live.flag_references["moving"] == "MOVING"
    assert live.control_mode == "MODE"
    assert live.model is None
    assert isinstance(design.components["gap"], ReadFloatScalar)
    assert not isinstance(design.components["gap"], ReadWriteFloatScalar)
    assert source.components["gap"] is None
    metadata = live.drives
    metadata["gap"]["unit"] = "m"
    assert design.components["gap"].unit() == live.drives["gap"]["unit"] == "mm"
    assert "InsertionDevice" in repr(live)


def test_fixed_reference_noops_and_rejected_writes(id_lattice_file):
    machine = _machine(id_lattice_file, [_device(control_mode="MODE", model_operating_point={"gap": 4.0, "mode": "parallel"})])
    device = machine.design.insertion_device.get("ID")
    drive = device.components["gap"]
    reference = device.model.reference
    assert drive.get_setpoint() == drive.get() == 4.0
    for disabled in (False, True):
        if disabled:
            device.model.disable()
        drive.set(4.0)
        drive.set_and_wait(4.0)
        device.model.mode = "parallel"
        for value in (5.0, float("nan")):
            with pytest.raises(PyAMLException, match="fixed model operating point"):
                drive.set_and_wait(value)
        with pytest.raises(PyAMLException, match="fixed model operating point"):
            drive.set(5.0)
        with pytest.raises(PyAMLException, match="fixed model operating point"):
            device.model.mode = "antiparallel"
        assert drive.get() == 4.0
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
