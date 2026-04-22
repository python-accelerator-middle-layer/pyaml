import pytest


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_dummy_tango_attributes_share_state(install_test_package):
    from tango.pyaml.attribute import Attribute
    from tango.pyaml.attribute import ConfigModel as AttributeConfigModel
    from tango.pyaml.attribute_store import get_attribute, set_attribute

    set_attribute("sr/test/device/value", 2.0, unit="mm", range=(0.0, 3.0))

    first = Attribute(AttributeConfigModel(attribute="sr/test/device/value"))
    second = Attribute(AttributeConfigModel(attribute="sr/test/device/value"))

    assert first.get() == 2.0
    assert second.get() == 2.0
    assert first.unit() == "mm"
    assert first.get_range() == [0.0, 3.0]

    second.set(2.5)

    assert first.get() == 2.5
    assert get_attribute("sr/test/device/value") == 2.5


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_dummy_tango_attribute_lookup_accepts_control_system_prefix(install_test_package):
    from tango.pyaml.attribute import Attribute
    from tango.pyaml.attribute import ConfigModel as AttributeConfigModel
    from tango.pyaml.attribute_store import set_attribute

    set_attribute("srdiag/bpm/c01-04/Position", [0.0, 1.0], unit="mm")

    attribute = Attribute(
        AttributeConfigModel(
            attribute="//ebs-simu-3:10000/srdiag/bpm/c01-04/Position",
            unit="mm",
        )
    )
    attribute.set_array(True)

    assert attribute.get() == [0.0, 1.0]
    assert attribute.unit() == "mm"


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_dummy_tango_read_only_attribute_can_be_initialized(install_test_package):
    from tango.pyaml.attribute_read_only import AttributeReadOnly
    from tango.pyaml.attribute_read_only import ConfigModel as ReadOnlyConfigModel
    from tango.pyaml.attribute_store import set_attribute

    set_attribute("srdiag/tune/tune_h", 0.37, unit="1")
    attribute = AttributeReadOnly(ReadOnlyConfigModel(attribute="srdiag/tune/tune_h"))

    assert attribute.get() == 0.37
    assert attribute.unit() == "1"
    with pytest.raises(Exception, match="read only attribute"):
        attribute.set(0.38)
