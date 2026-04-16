import pytest

from pyaml import PyAMLConfigException
from pyaml.accelerator import Accelerator


def test_accelerator_load_rejects_non_accelerator_root(tmp_path):
    config_file = tmp_path / "quadrupole.yaml"
    config_file.write_text("type: pyaml.magnet.quadrupole\nname: QF1A-C01\n", encoding="utf-8")

    with pytest.raises(PyAMLConfigException, match="Accelerator.load\\(\\) expects a 'pyaml.accelerator' root"):
        Accelerator.load(str(config_file))
