import pytest

from pyaml import PyAMLException
from pyaml.magnet.hcorrector import HCorrector


@pytest.mark.parametrize(
    ("accessor", "unit"),
    [("strength", "physics"), ("hardware", "hardware")],
)
def test_missing_model_error_names_magnet_without_repr_recursion(accessor, unit):
    magnet = HCorrector("CH1").attach(object(), strength=None, hardware=None)

    with pytest.raises(PyAMLException, match=f"CH1 has no model that supports {unit} units"):
        getattr(magnet, accessor)
