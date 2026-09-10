import pytest
from pydantic import BaseModel, ConfigDict

from pyaml import PyAMLConfigException, set_repr_options
from pyaml.accelerator import Accelerator, ElementHolder
from pyaml.common.element import Element, ElementConfigModel, __pyaml_repr__
from pyaml.control.controlsystem import ControlSystemAdapter


def test_peer():
    sr = Accelerator.load("tests/config/tune_monitor.yaml")
    tm = sr.design.get_betatron_tune_monitor("BETATRON_TUNE")
    assert isinstance(tm.peer.peer, Accelerator)
    assert isinstance(tm.peer, ElementHolder)
    tm = sr.live.get_betatron_tune_monitor("BETATRON_TUNE")
    assert isinstance(tm.peer.peer, Accelerator)
    assert isinstance(tm.peer, ElementHolder)


def test_repr_is_informative_and_bounded():
    sr = Accelerator.load("tests/config/EBSOrbit.yaml")
    bpm = sr.design.bpm.get("BPM_C04-04")
    bpms = sr.design.bpms.get("BPM")

    assert repr(bpm) == "BPM(name='BPM_C04-04', lattice_names='BPM_C04-04', peer=Simulator:design)"
    assert repr(sr.design) == (
        f"Simulator(name='design', lattice={sr.design.lattice!r}, mat_key=None, n_elements={len(sr.design.ring)})"
    )
    assert repr(sr) == "Accelerator(facility='ESRF', machine='sr', simulators=['design'], controls=['live'])"
    assert len(repr(bpms)) < 250
    assert f"size={len(bpms)}" in repr(bpms)
    assert f"... +{len(bpms) - 3} more ..." in repr(bpms)


def test_repr_options_limit_sequences():
    original = set_repr_options()
    try:
        set_repr_options(max_items=1)
        sr = Accelerator.load("tests/config/EBSOrbit.yaml")

        bpms = sr.design.bpms.get("BPM")
        assert f"... +{len(bpms) - 1} more ..." in repr(bpms)
    finally:
        set_repr_options(
            max_items=original.max_items,
            max_depth=original.max_depth,
            max_length=original.max_length,
        )


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
    dconfig: dict


class MyControlSystem(ControlSystemAdapter):
    def __init__(self, cfg: MyControlSystemConfigModel):
        ControlSystemAdapter.__init__(self)
        self._cfg = cfg

    def name(self) -> str:
        return self._cfg.name

    def dconfig(self) -> dict:
        return self._cfg.dconfig

    def __repr__(self):
        return __pyaml_repr__(self)


class MyElementConfigModel(ElementConfigModel):
    device_h: str
    device_v: str


class MyElement(Element):
    def __init__(self, cs: MyControlSystem, cfg: MyElementConfigModel):
        Element.__init__(self, cfg.name)
        self._cfg = cfg


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
                "dconfig": {"prefix": "VA:", "info": {"param1": "Param1 value", "param2": 12345.0}},
            }
        ],
        "devices": [
            {
                "type": MyElement.__module__,
                "class": "MyElement",
                "validation_class": "MyElementConfigModel",
                "name": "MY_ELEMENT",
                "control_modes": ["live"],
                "device_h": "TUNEZR:rdH",
                "device_v": "TUNEZR:rdV",
            }
        ],
    }

    sr = Accelerator.from_dict(acc_config)
    assert sr.live.dconfig()["prefix"] == "VA:"
    assert sr.live.dconfig()["info"]["param1"] == "Param1 value"
    assert sr.live.dconfig()["info"]["param2"] == 12345.0
    assert isinstance(sr.live.get_element("MY_ELEMENT"), MyElement)
    assert sr.live.get_element("MY_ELEMENT")._cfg.device_h == "TUNEZR:rdH"
