import pytest

from pyaml import PyAMLConfigException
from pyaml.accelerator import Accelerator


def test_accelerator_load_rejects_non_accelerator_root(tmp_path):
    config_file = tmp_path / "quadrupole.yaml"
    config_file.write_text("type: pyaml.magnet.quadrupole\nname: QF1A-C01\n", encoding="utf-8")

    with pytest.raises(PyAMLConfigException, match="Accelerator.load\\(\\) expects a 'pyaml.accelerator' root"):
        Accelerator.load(str(config_file))


def test_accelerator_load_supports_remote_sources(http_config_server, ebs_lattice_file):
    routes = {
        "/config/accelerator.yaml": """
type: pyaml.accelerator
facility: Remote Facility
machine: remote_ring
energy: 3000000000.0
data_folder: remote-data
description: Remote accelerator
simulators: fragments/simulators.json
devices: []
""",
        "/config/fragments/simulators.json": f"""
[
  {{
    "type": "pyaml.lattice.simulator",
    "name": "design",
    "lattice": "{ebs_lattice_file.as_posix()}"
  }}
]
""",
    }

    with http_config_server(routes) as base_url:
        accelerator = Accelerator.load(f"{base_url}/config/accelerator.yaml")

    assert isinstance(accelerator, Accelerator)
    assert accelerator.design.name() == "design"
    assert accelerator.get_description() == "Remote accelerator"
