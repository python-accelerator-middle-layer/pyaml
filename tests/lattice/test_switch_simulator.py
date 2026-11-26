from unittest.mock import Mock

import pytest
import yaml

from pyaml.accelerator import Accelerator
from pyaml.common.exception import PyAMLException
from pyaml.common.switch_element import SwitchElement
from pyaml.control.controlsystem import ControlSystemAdapter
from pyaml.lattice.abstract_impl import RWBooleanScalar
from pyaml.lattice.simulator import Simulator
from pyaml.validation import register_schema
from pyaml.validation.schema_builder import generate_configuration_schema


@register_schema
class SwitchTestControlSystem(ControlSystemAdapter):
    def __init__(self, name: str):
        super().__init__()
        self._name = name

    def name(self) -> str:
        return self._name


@pytest.fixture
def design(ebs_lattice_file):
    return Simulator(name="design", lattice=str(ebs_lattice_file))


def test_simulated_switch_bypasses_lattice_lookup(design, monkeypatch):
    lookup = Mock(side_effect=AssertionError("Switch must not resolve a lattice element"))
    monkeypatch.setattr(design, "get_at_elems", lookup)
    monkeypatch.setattr(design, "_linker", Mock())
    monkeypatch.setattr(design, "ring", Mock())
    configured = SwitchElement("NO_LATTICE_EQUIVALENT", "UNRESOLVED_DEVICE")

    design.fill_device([configured])
    switch = design["NO_LATTICE_EQUIVALENT"]

    assert switch is not configured
    assert switch.peer is design
    assert configured.peer is None
    assert switch.enabled.get() is False
    switch.enabled.set(True)
    assert switch.enabled.get() is True
    switch.disable()
    assert switch.is_enabled() is False
    switch.enable()
    assert switch.enabled.get() is True
    switch.enabled.set(False)
    assert switch.enabled.get() is False
    lookup.assert_not_called()
    assert design._linker.mock_calls == []
    assert design.ring.mock_calls == []


@pytest.mark.parametrize("value", [1, "true"])
def test_simulated_boolean_accessor_rejects_invalid_writes_without_changing_state(value):
    enabled = RWBooleanScalar("SOFB")
    enabled.set(True)

    with pytest.raises(PyAMLException, match="SOFB: expected a boolean flag"):
        enabled.set(value)

    assert enabled.get() is True


def test_simulated_state_is_independent_per_element_and_mode(design, ebs_lattice_file):
    configured = SwitchElement("SOFB", "SOFB_ENABLED")
    design.fill_device([configured, SwitchElement("FOFB", "FOFB_ENABLED")])
    design["SOFB"].enabled.set(True)
    other = Simulator(name="other", lattice=str(ebs_lattice_file))
    other.fill_device([configured])

    assert design["SOFB"].is_enabled() is True
    assert design["FOFB"].is_enabled() is False
    assert other["SOFB"].is_enabled() is False
    other["SOFB"].enable()
    design["SOFB"].disable()
    assert other["SOFB"].is_enabled() is True
    assert configured.peer is None


def test_duplicate_registration_does_not_replace_simulated_switch(design):
    design.fill_device([SwitchElement("SOFB", "SOFB_ENABLED")])
    original = design["SOFB"]

    with pytest.raises(PyAMLException, match="Duplicate element"):
        design.fill_device([SwitchElement("SOFB", "OTHER_CHANNEL")])

    assert design["SOFB"] is original


def test_accelerator_configuration_keeps_live_and_simulated_state_separate(tmp_path, ebs_lattice_file, monkeypatch):
    from tango.pyaml.attribute import Attribute
    from tango.pyaml.attribute import ConfigModel as AttributeConfigModel
    from tango.pyaml.attribute_store import get_attribute, set_attribute

    device_name = "switch-tests/feedback/enabled"
    set_attribute(device_name, True)
    monkeypatch.setattr(
        ControlSystemAdapter,
        "get_device_access",
        lambda self, ref: None if ref is None else Attribute(AttributeConfigModel(attribute=ref)),
    )
    for cls in (SwitchElement, SwitchTestControlSystem, Simulator, Accelerator):
        generate_configuration_schema(cls)
    config = {
        "class": "pyaml.accelerator.Accelerator",
        "facility": "Test",
        "machine": "ring",
        "energy": 3e9,
        "controls": [{"class": f"{__name__}.SwitchTestControlSystem", "name": "live"}],
        "simulators": [{"type": "pyaml.lattice.simulator", "name": "design", "lattice": str(ebs_lattice_file)}],
        "devices": [
            {"class": "pyaml.common.switch_element.SwitchElement", "name": "SOFB", "device": device_name},
            {"type": "pyaml.diagnostics.bpm.bpm", "name": "BPM_C04-01"},
        ],
    }
    config_path = tmp_path / "switch.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    set_spy = Mock(side_effect=AssertionError("Loading must not write live hardware"))
    with monkeypatch.context() as patch:
        patch.setattr(Attribute, "set", set_spy)
        sr = Accelerator.load(str(config_path), validate=True)

    set_spy.assert_not_called()
    assert sr.live["SOFB"].peer is sr.live
    assert sr.design["SOFB"].peer is sr.design
    assert sr.live["SOFB"].enabled.get() is True
    assert sr.design["SOFB"].enabled.get() is False
    assert sr.design.diagnostic.bpm["BPM_C04-01"] is not None
    sr.design["SOFB"].enabled.set(True)
    sr.design["SOFB"].disable()
    assert get_attribute(device_name) is True

    sr.live["SOFB"].enabled.set(False)
    assert sr.live["SOFB"].enabled.get() is False
    sr.design["SOFB"].enable()
    assert sr.live["SOFB"].is_enabled() is False
    sr.live["SOFB"].enable()
    assert sr.live["SOFB"].is_enabled() is True
    assert sr.design["SOFB"].is_enabled() is True
