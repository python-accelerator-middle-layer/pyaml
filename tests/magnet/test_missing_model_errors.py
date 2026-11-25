import pytest

from pyaml import PyAMLException
from pyaml.magnet.hcorrector import HCorrector


def test_missing_model_errors_name_magnet_without_formatting_it():
    magnet = HCorrector("CH1").attach(object(), strength=None, hardware=None)

    with pytest.raises(PyAMLException, match="CH1 has no model that supports physics units"):
        _ = magnet.strength

    with pytest.raises(PyAMLException, match="CH1 has no model that supports hardware units"):
        _ = magnet.hardware

    assert "CH1" in repr(magnet)
