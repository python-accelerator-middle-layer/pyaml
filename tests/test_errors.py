import pytest

from pyaml.accelerator import Accelerator
from pyaml.arrays.magnet_array import MagnetArray
from pyaml.common.exception import PyAMLConfigException, PyAMLException


@pytest.mark.parametrize(
    "install_test_package",
    [{"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"}],
    indirect=True,
)
def test_tune(install_test_package):
    with pytest.raises(PyAMLConfigException) as exc:
        ml: Accelerator = Accelerator.load("tests/config/bad_conf_duplicate_1.yaml")
    assert "MagnetArray HCORR : duplicate name SH1A-C02-H @index 2" in str(exc)

    with pytest.raises(PyAMLConfigException) as exc:
        ml: Accelerator = Accelerator.load("tests/config/bad_conf_duplicate_2.yaml")
    assert "BPMArray BPM : duplicate name BPM_C04-06 @index 3" in str(exc)

    with pytest.raises(PyAMLConfigException) as exc:
        ml: Accelerator = Accelerator.load("tests/config/bad_conf_duplicate_3.yaml")
    assert "Configuration entry 'BPM_C04-06' is duplicated inside category 'devices'" in str(exc)
    assert "bad_conf_duplicate_3.yaml" in str(exc)

    with pytest.raises(PyAMLConfigException) as exc:
        ml: Accelerator = Accelerator.load("tests/config/bad_conf_duplicate_4.yaml")
    assert "MagnetArray HCORR : duplicate name SH1A-C02-H @index 2" in str(exc)

    sr: Accelerator = Accelerator.load("tests/config/EBSTune.yaml")
    m1 = sr.live.get_magnet("QF1E-C04")
    m2 = sr.design.get_magnet("QF1A-C05")
    with pytest.raises(PyAMLException) as exc:
        ma = MagnetArray("Test", [m1, m2])
    assert "MagnetArray Test: All elements must be attached to the same instance" in str(exc)

    with pytest.raises(PyAMLException) as exc:
        m2 = sr.design.get_magnet("QF1A-C05XX")
    assert "Magnet QF1A-C05XX not defined" in str(exc)

    with pytest.raises(PyAMLException) as exc:
        m2 = sr.design.get_bpm("QF1A-C05XX")
    assert "BPM QF1A-C05XX not defined" in str(exc)
