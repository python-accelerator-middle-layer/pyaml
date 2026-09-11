from pathlib import Path

from pyaml.accelerator import Accelerator


def test_load_conf_with_code():
    parent_folder = Path(__file__).parent
    config_path = parent_folder.joinpath("config", "EBSOrbit.yaml").resolve()

    sr: Accelerator = Accelerator.load(config_path)
    bpms = sr.live.bpms.get("BPM")
    assert bpms is not None
    assert len(bpms) == 320

    assert sr.live[bpms[0].get_name()] is bpms[0]
    assert sr.live["BPM*"].names() == bpms.names()
    assert sr.live[:].names() == [element.get_name() for element in sr.live.get_all_elements()]
    assert sr.design["BPM*"].names() == sr.design.bpms.get("BPM").names()
