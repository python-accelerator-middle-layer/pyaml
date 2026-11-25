import numpy as np
import pytest

from pyaml.common.exception import PyAMLException
from pyaml.configuration.factory import Factory
from pyaml.magnet.linear_serialized_with_trims_model import LinearSerializedMagnetWithTrimsModel
from pyaml.magnet.trim_coil import TrimCoil


@pytest.fixture
def model():
    result = Factory.build(
        {
            "type": "pyaml.magnet.linear_serialized_with_trims_model",
            "curves": {
                "type": "pyaml.magnet.inline_curve",
                "mat": [[0, 0], [1, 1], [2, 4], [3, 9], [4, 16]],
            },
            "calibration_factors": [1, 2, 3],
            "calibration_offsets": 0.5,
            "unit": "rad",
            "hardware_unit": "A",
            "powerconverter": "main/current",
            "trims": [
                {
                    "class": "pyaml.magnet.trim_coil.TrimCoil",
                    "element": "D3",
                    "name": "T3",
                    "powerconverter": "trim3/current",
                    "trim_factor": -0.5,
                },
                {
                    "class": "pyaml.magnet.trim_coil.TrimCoil",
                    "element": "D1",
                    "name": "T1",
                    "powerconverter": "trim1/current",
                    "trim_factor": 0.5,
                },
            ],
        }
    )
    result.set_elements(["D1", "D2", "D3"])
    result.set_magnet_rigidity(2.0)
    return result


def test_configuration_and_main_series(model):
    assert isinstance(model, LinearSerializedMagnetWithTrimsModel)
    assert model.get_device_names() == ["main/current"]
    assert model.get_trim_device_names() == ["trim3/current", "trim1/current"]
    assert model.get_trim_hardware_units() == ["A", "A"]
    assert model.get_strength_units() == ["rad"] * 3
    strengths = model.compute_strengths([2.0])
    np.testing.assert_allclose(strengths, [2.25, 4.25, 6.25])
    np.testing.assert_allclose(model.compute_hardware_values(strengths), [2.0])
    assert model.compute_mean_strength(2.0) == pytest.approx(4.25)


def test_trim_conversions_at_different_main_currents(model):
    # Trim order differs from member order; offsets cancel in the difference.
    for index, trim_current, expected in [(0, -1.0, 3.75), (1, 1.0, 1.25)]:
        strength = model.compute_trim_strength(index, 2.0, trim_current)
        assert strength == pytest.approx(expected)
        assert model.compute_trim_current(index, 2.0, strength) == pytest.approx(trim_current)
        assert model.compute_trim_strength(index, 1.0, trim_current) != pytest.approx(strength)
        assert model.compute_trim_strength(index, 2.0, 0.0) == pytest.approx(0.0)
    model.set_magnet_rigidity(4.0)
    assert model.compute_trim_strength(1, 2.0, 1.0) == pytest.approx(0.625)


def test_trim_target_binding(model):
    with pytest.raises(PyAMLException, match="Trim target"):
        model.set_elements(["D1", "D2", "UNKNOWN"])
    model.set_number_of_magnets(3)
    with pytest.raises(PyAMLException, match="set_elements"):
        model.compute_trim_strength(0, 2.0, 1.0)


def test_trim_configuration_schema():
    from pyaml.validation import SchemaRegistry, SchemaValidator

    class_path = f"{LinearSerializedMagnetWithTrimsModel.__module__}.{LinearSerializedMagnetWithTrimsModel.__name__}"
    registered = SchemaRegistry().get(class_path)
    assert "TrimCoil" in registered.describe()
    trim_class_path = f"{TrimCoil.__module__}.{TrimCoil.__name__}"
    assert "trim_factor: float" in SchemaRegistry()[trim_class_path].describe()
    schema = registered.model_json_schema()
    trim_schema = schema["properties"]["trims"]["items"]
    assert set(trim_schema["required"]) == {"class", "element", "name", "powerconverter"}
    assert trim_schema["properties"]["trim_factor"]["default"] == 1.0
    assert trim_schema["properties"]["hardware_unit"]["default"] is None
    assert trim_schema["additionalProperties"] is False

    config = {
        "class": class_path,
        "curves": {"type": "pyaml.magnet.inline_curve", "mat": [[0, 0], [1, 1]]},
        "hardware_unit": "A",
        "trims": [
            {"class": "pyaml.magnet.trim_coil.TrimCoil", "element": "D1", "name": "T1", "powerconverter": "trim/current"}
        ],
    }
    validated = SchemaValidator.validate_to_dict(config)
    assert validated["trims"][0]["trim_factor"] == 1.0
    built = Factory.build(validated)
    assert isinstance(built.trims[0], TrimCoil)
    assert built.get_trim_hardware_units() == ["A"]

    # Nested validation catches both missing fields and invalid field types.
    from pyaml.common.exception import PyAMLConfigException

    for trim in [{"element": "D1"}, {**config["trims"][0], "trim_factor": "invalid"}]:
        with pytest.raises(PyAMLConfigException):
            SchemaValidator.validate_to_dict({**config, "trims": [trim]})
