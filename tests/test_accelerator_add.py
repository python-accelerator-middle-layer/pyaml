import copy

import pytest

from pyaml.accelerator import Accelerator
from pyaml.common.element import Element
from pyaml.common.exception import PyAMLException
from pyaml.diagnostics.tune_monitor import BetatronTuneMonitor
from pyaml.magnet.identity_model import IdentityMagnetModel
from pyaml.magnet.quadrupole import Quadrupole
from pyaml.tuning_tools.orbit import Orbit
from pyaml.tuning_tools.tune import Tune
from pyaml.tuning_tools.tune_response_matrix import TuneResponseMatrix
from pyaml.tuning_tools.tuning_tool import TuningTool


class TrackingElement(Element):
    def __init__(self, name):
        super().__init__(name)
        self.energy = None
        self.alphac = None
        self.harmonic_number = None
        self.post_init_count = 0

    def _fill_device(self, holder):
        instance = copy.copy(self)
        instance._peer = holder
        holder.add_element(instance)

    def set_energy(self, energy):
        self.energy = energy

    def set_mcf(self, alphac):
        self.alphac = alphac

    def set_harmonic(self, harmonic_number):
        self.harmonic_number = harmonic_number

    def post_init(self):
        self.check_peer()
        assert self.energy is not None
        self.post_init_count += 1


@pytest.fixture
def accelerator_factory(simulator_fragment_factory):
    def build(simulators=("design", "simulation"), controls=("live", "control")):
        return Accelerator.from_dict(
            {
                "type": "pyaml.accelerator",
                "facility": "TEST",
                "machine": "sr",
                "energy": 6e9,
                "alphac": 1e-4,
                "harmonic_number": 992,
                "simulators": [simulator_fragment_factory(name) for name in simulators],
                "controls": [{"type": "tango.pyaml.controlsystem", "name": name} for name in controls],
                "devices": [],
            }
        )

    return build


@pytest.mark.parametrize(
    ("simulators", "controls"),
    [
        (("design", "simulation"), ("live", "control")),
        (("design", "simulation"), ()),
        ((), ("live", "control")),
        ((), ()),
        (("shared",), ("shared",)),
    ],
)
def test_add_binds_and_initializes_only_new_instances(accelerator_factory, simulators, controls):
    accelerator = accelerator_factory(simulators, controls)
    holders = [*accelerator.simulators().values(), *accelerator.controls().values()]
    existing = TrackingElement("EXISTING")
    accelerator.add(existing)
    element = TrackingElement("NEW_ELEMENT")

    assert accelerator.add(element) is None

    instances = []
    for holder in holders:
        attached = holder[element.name]
        instances.append(attached)
        assert attached is not element
        assert attached.peer is holder
        assert attached.peer.peer is accelerator
        assert (attached.energy, attached.alphac, attached.harmonic_number) == (6e9, 1e-4, 992)
        assert attached.post_init_count == 1
        assert holder[existing.name].post_init_count == 1
    assert len({id(attached) for attached in instances}) == len(holders)
    assert element.peer is None
    assert element.energy is None
    assert element.post_init_count == 0
    assert accelerator._devices == [existing, element]


def test_add_uses_current_accelerator_properties(accelerator_factory):
    accelerator = accelerator_factory()
    accelerator.set_energy(3e9)
    accelerator.set_mcf(2e-4)
    accelerator.set_harmonic_number(400)

    accelerator.add(TrackingElement("NEW_ELEMENT"))

    for holder in accelerator.modes().values():
        attached = holder["NEW_ELEMENT"]
        assert (attached.energy, attached.alphac, attached.harmonic_number) == (3e9, 2e-4, 400)


@pytest.mark.parametrize("tool_type", [Tune, TuneResponseMatrix])
def test_add_binds_tune_tools_to_each_modes_devices(tool_type, config_root_path):
    accelerator = Accelerator.load("tests/config/EBSTune.yaml")
    kwargs = {"name": "ALTUNE", "quad_array_name": "QForTune", "betatron_tune_name": "BETATRON_TUNE"}
    if tool_type is Tune:
        kwargs["response_matrix"] = str(config_root_path / "tune_response.json")
    else:
        kwargs["quad_delta"] = 1e-4
    tool = tool_type(**kwargs)

    accelerator.add(tool)

    for holder in accelerator.modes().values():
        attached = holder.tool.get("ALTUNE")
        assert isinstance(attached, tool_type)
        assert attached is holder["ALTUNE"]
        assert attached.peer is holder
        assert attached.tune_monitor is holder.diagnostic.get("BETATRON_TUNE")
        assert attached.quadrupoles is holder.magnets.get("QForTune")
    assert tool.peer is None
    assert accelerator.design.tool.get("ALTUNE") is not accelerator.live.tool.get("ALTUNE")
    assert accelerator.yellow_pages.availability("ALTUNE") == {"design", "live"}


def test_add_initializes_orbit_handles(config_root_path):
    accelerator = Accelerator.load("tests/config/EBSOrbit.yaml")
    tool = Orbit(
        name="ALTORBIT",
        bpm_array_name="BPM",
        hcorr_array_name="HCorr",
        vcorr_array_name="VCorr",
        response_matrix=str(config_root_path / "ideal_orm_disp.json"),
        rf_plant_name="DEFAULT_RF_PLANT",
        singular_values=1,
    )

    accelerator.add(tool)

    for holder in accelerator.modes().values():
        attached = holder.tool.get(tool.name)
        assert attached.correctors.names() == holder.magnets.get("HCorr").names() + holder.magnets.get("VCorr").names()
        assert all(corrector.peer is holder for corrector in attached.correctors)
        assert attached.rf_plant is holder.rf.get("DEFAULT_RF_PLANT")
    assert tool.peer is None


def test_add_registers_diagnostics_in_every_mode(accelerator_factory):
    accelerator = accelerator_factory()
    monitor = BetatronTuneMonitor("NEW_TUNE")

    accelerator.add(monitor)

    for holder in accelerator.modes().values():
        attached = holder.diagnostic.get(monitor.name)
        assert attached is holder[monitor.name]
        assert attached.peer is holder
        assert attached is not monitor
        assert attached._h == 992
    assert monitor.peer is None
    assert accelerator.yellow_pages.availability(monitor.name) == set(accelerator.modes())


def test_add_binds_magnet_strength_to_the_lattice(accelerator_factory):
    accelerator = accelerator_factory(controls=())
    magnet = Quadrupole(
        "NEW_QUAD",
        lattice_names="QF1A-C01@0",
        model=IdentityMagnetModel(physics="QUAD_STRENGTH", unit="1/m"),
    )

    accelerator.add(magnet)
    accelerator.design.magnet.get(magnet.name).strength.set(0.5)

    assert accelerator.design.magnet.get(magnet.name).strength.get() == pytest.approx(0.5)
    assert accelerator.simulation.magnet.get(magnet.name).strength.get() != pytest.approx(0.5)
    assert magnet.peer is None


@pytest.mark.parametrize("existing_element", [TuningTool("DUPLICATE"), Element("DUPLICATE")])
def test_add_rejects_duplicate_names_before_registering_any_instances(accelerator_factory, existing_element):
    accelerator = accelerator_factory()
    accelerator.control.add_element(existing_element)

    with pytest.raises(PyAMLException, match="Duplicate element DUPLICATE in mode control"):
        accelerator.add(TrackingElement("DUPLICATE"))

    assert accelerator.control["DUPLICATE"] is existing_element
    for holder in (accelerator.design, accelerator.simulation, accelerator.live):
        assert "DUPLICATE" not in holder.get().names()
    assert accelerator._devices == []


@pytest.mark.parametrize("mode", ["design", "simulation", "live", "control"])
@pytest.mark.parametrize("register_before_failure", [False, True])
def test_add_rolls_back_binding_failure(accelerator_factory, monkeypatch, mode, register_before_failure):
    accelerator = accelerator_factory()
    existing = TrackingElement("EXISTING")
    existing_tool = TuningTool("EXISTING_TOOL")
    accelerator.add(existing)
    accelerator.add(existing_tool)
    holders = accelerator.modes()
    snapshots = {name: holder._ALL.copy() for name, holder in holders.items()}
    holder = holders[mode]
    fill_device = holder.fill_device
    element = BetatronTuneMonitor("NEW_TUNE")
    error = PyAMLException("Backend binding failed") if register_before_failure else RuntimeError("Backend binding failed")

    def fail_binding(elements):
        if register_before_failure:
            fill_device(elements)
            fill_device([TuningTool("HELPER_TOOL")])
        raise error

    monkeypatch.setattr(holder, "fill_device", fail_binding)

    with pytest.raises(
        PyAMLException,
        match=f"Failed to add element NEW_TUNE in mode {mode}: Backend binding failed",
    ) as exc_info:
        accelerator.add(element)

    assert exc_info.value.__cause__ is error
    assert accelerator._devices == [existing, existing_tool]
    for name, holder in holders.items():
        assert holder._ALL == snapshots[name]
        assert holder._DIAG == {}
        assert holder.tool.get(existing_tool.name) is snapshots[name][existing_tool.name]
        assert list(holder._TOOLS) == [existing_tool.name]
        assert holder[existing.name].post_init_count == 1

    monkeypatch.setattr(holders[mode], "fill_device", fill_device)
    accelerator.add(element)
    for holder in holders.values():
        assert holder.diagnostic.get(element.name) is holder[element.name]
    assert accelerator.yellow_pages.availability(element.name) == set(holders)


@pytest.mark.parametrize("method", ["set_energy", "set_mcf", "set_harmonic", "post_init"])
def test_add_rolls_back_initialization_failure(accelerator_factory, monkeypatch, method):
    accelerator = accelerator_factory()
    existing = TrackingElement("EXISTING")
    accelerator.add(existing)
    holders = accelerator.modes()
    snapshots = {name: holder._ALL.copy() for name, holder in holders.items()}
    original_method = getattr(TrackingElement, method)
    error = RuntimeError("Initialization failed")

    def fail_initialization(self, *args):
        if self.peer.name() == "live":
            raise error
        original_method(self, *args)

    monkeypatch.setattr(TrackingElement, method, fail_initialization)

    with pytest.raises(
        PyAMLException,
        match="Failed to add element NEW_ELEMENT in mode live: Initialization failed",
    ) as exc_info:
        accelerator.add(TrackingElement("NEW_ELEMENT"))

    assert exc_info.value.__cause__ is error
    assert accelerator._devices == [existing]
    for name, holder in holders.items():
        assert holder._ALL == snapshots[name]
        assert holder[existing.name].post_init_count == 1


@pytest.mark.parametrize("invalid_element", [None, {}, object()])
def test_add_rejects_non_elements(accelerator_factory, invalid_element):
    accelerator = accelerator_factory(simulators=(), controls=())

    with pytest.raises(TypeError, match="Accelerator.add\\(\\) expects an Element"):
        accelerator.add(invalid_element)


def test_add_device_uses_the_same_binding_and_initialization(accelerator_factory):
    accelerator = accelerator_factory()

    accelerator.add_device({"type": "pyaml.diagnostics.tune_monitor", "name": "NEW_TUNE"})

    for holder in accelerator.modes().values():
        monitor = holder.diagnostic.get("NEW_TUNE")
        assert monitor.peer is holder
        assert monitor._h == 992
    assert accelerator._devices[0].name == "NEW_TUNE"
