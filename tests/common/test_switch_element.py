from unittest.mock import create_autospec

import pytest

from pyaml.common import abstract
from pyaml.common.exception import PyAMLConfigException, PyAMLException
from pyaml.common.switch_element import SwitchElement
from pyaml.configuration.factory import Factory
from pyaml.control.controlsystem import ControlSystemAdapter
from pyaml.validation import SchemaGenerator, SchemaRegistry, SchemaValidator
from pyaml.validation.schema_builder import generate_configuration_schema
from tests.common.test_element_holder import DispatchHolder

CLASS_PATH = "pyaml.common.switch_element.SwitchElement"


@pytest.fixture
def switch():
    return SwitchElement("SOFB", "SOFB_ENABLED", description="Slow orbit feedback")


@pytest.mark.parametrize("operation", ["enable", "disable", "is_enabled", "enabled"])
def test_unattached_operations_raise(switch, operation):
    with pytest.raises(PyAMLException, match="SOFB: enabled state is unavailable before attachment"):
        value = getattr(switch, operation)
        if operation != "enabled":
            value()


def test_attachment_copies_configuration_without_io(switch):
    state = create_autospec(abstract.RWScalarBoolean, instance=True)
    peer = create_autospec(ControlSystemAdapter, instance=True)
    peer.name.return_value = "live"

    attached = switch.attach(peer, state)

    assert attached is not switch
    assert attached.peer is peer
    assert attached.name == "SOFB"
    assert attached.device == "SOFB_ENABLED"
    assert attached.description == "Slow orbit feedback"
    assert switch.peer is None
    assert "SwitchElement(name='SOFB'" in repr(attached)
    assert "SOFB_ENABLED" in repr(attached)
    assert "unavailable" not in repr(attached)
    assert state.mock_calls == []


def test_element_delegates_to_boolean_accessor(switch):
    enabled = create_autospec(abstract.RWScalarBoolean, instance=True)
    attached = switch.attach(DispatchHolder(), enabled=enabled)

    attached.enable()
    enabled.set.assert_called_once_with(True)
    enabled.get.assert_not_called()
    enabled.reset_mock()
    attached.disable()
    enabled.set.assert_called_once_with(False)
    enabled.get.assert_not_called()
    enabled.get.return_value = False
    assert attached.is_enabled() is False
    enabled.get.assert_called_once_with()


def test_unsupported_holder_raises_without_new_abstract_requirement(switch):
    holder = DispatchHolder()

    with pytest.raises(PyAMLException, match="DispatchHolder does not support switch element SOFB"):
        holder.fill_device([switch])

    assert holder.get().names() == []


@pytest.mark.parametrize(
    "declaration",
    [
        {"class": CLASS_PATH},
        {"class_path": CLASS_PATH},
        {"type": "pyaml.common.switch_element"},
    ],
)
def test_factory_and_schema_support_class_and_legacy_declarations(declaration):
    Factory.clear()
    generate_configuration_schema(SwitchElement)
    try:
        config = {**declaration, "name": "SOFB", "device": "SOFB_ENABLED"}
        validated = SchemaValidator.validate_to_dict(config)
        switch = Factory.build(validated)

        assert isinstance(switch, SwitchElement)
        assert switch.name == "SOFB"
        assert switch.device == "SOFB_ENABLED"
        assert switch.peer is None
    finally:
        Factory.clear()


def test_schema_is_discoverable_and_requires_one_device():
    registry = SchemaRegistry()
    registry.discover()
    schema = SchemaGenerator.generate(CLASS_PATH)

    assert registry.get(CLASS_PATH) is not None
    assert {"name", "device"} <= set(schema["required"])
    assert schema["properties"]["device"]["type"] == "string"
    assert "initial_enabled" not in schema["properties"]


@pytest.mark.parametrize("device", [None, True, 1, ["SOFB_ENABLED"]])
def test_constructor_rejects_non_string_device(device):
    with pytest.raises(PyAMLConfigException):
        SwitchElement("SOFB", device)


def test_schema_rejects_extra_configuration():
    generate_configuration_schema(SwitchElement)

    with pytest.raises(PyAMLConfigException, match="initial_enabled"):
        SchemaValidator.validate_to_dict(
            {"class": CLASS_PATH, "name": "SOFB", "device": "SOFB_ENABLED", "initial_enabled": True}
        )
