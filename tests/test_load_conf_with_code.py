from pathlib import Path

from pyaml.accelerator import Accelerator


def test_load_conf_with_code():
    parent_folder = Path(__file__).parent
    config_path = parent_folder.joinpath("config", "EBSOrbit.yaml").resolve()

    sr: Accelerator = Accelerator.load(config_path)
    bpms = sr.live.get_bpms("BPM")
    assert bpms is not None
    assert len(bpms) == 320
