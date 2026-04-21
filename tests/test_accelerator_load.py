import pytest
from pydantic import BaseModel, ConfigDict

from pyaml import PyAMLConfigException
from pyaml.accelerator import Accelerator, ElementHolder
from pyaml.common.element import __pyaml_repr__
from pyaml.configuration.cfg_dict import CfgDict
from pyaml.control.controlsystem import ControlSystemAdapter


def test_peer():
    sr = Accelerator.load("tests/config/tune_monitor.yaml")
    tm = sr.design.get_betatron_tune_monitor("BETATRON_TUNE")
    assert isinstance(tm.peer.peer, Accelerator)
    assert isinstance(tm.peer, ElementHolder)
    tm = sr.live.get_betatron_tune_monitor("BETATRON_TUNE")
    assert isinstance(tm.peer.peer, Accelerator)
    assert isinstance(tm.peer, ElementHolder)


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


class MyControlSystemConfigModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")
    name: str
    dconfig: CfgDict


class MyControlSystem(ControlSystemAdapter):
    def __init__(self, cfg: MyControlSystemConfigModel):
        ControlSystemAdapter.__init__(self)
        self._cfg = cfg

    def name(self) -> str:
        return self._cfg.name

    def dconfig(self) -> dict:
        return self._cfg.dconfig.get()

    def __repr__(self):
        return __pyaml_repr__(self)


def test_config_dict():
    acc_config = {
        "type": "pyaml.accelerator",
        "facility": "ACC",
        "machine": "sr",
        "energy": 1e9,
        "data_folder": "/data/store",
        "controls": [
            {
                "type": MyControlSystem.__module__,
                "class": "MyControlSystem",
                "validation_class": "MyControlSystemConfigModel",
                "name": "live",
                "dconfig": {
                    "type": "pyaml.configuration.cfg_dict",
                    "prefix": "VA:",
                    "info": {"param1": "Param1 value", "param2": 12345.0},
                },
            }
        ],
        "devices": [],
    }

    sr = Accelerator.from_dict(acc_config)
    assert sr.live.dconfig()["prefix"] == "VA:"
    assert sr.live.dconfig()["info"]["param1"] == "Param1 value"
    assert sr.live.dconfig()["info"]["param2"] == 12345.0
