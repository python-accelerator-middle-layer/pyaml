# ruff: noqa: E501
from pathlib import Path

from pyaml.accelerator import Accelerator

ebs_orbit_str_repr = """Controls:
    live
    .

Simulators:
    design
    .

Use <mode> from Controls or Simulators and <name> from the relevant group.

diagnostic.bpms:
    Access: accelerator.<mode>.diagnostic.bpms.get("<name>")
    BPM                   (pyaml.arrays.bpm_array)                size=320
    .

magnets:
    Access: accelerator.<mode>.magnets.get("<name>")
    HCorr                 (pyaml.arrays.magnet_array)             size=288
    VCorr                 (pyaml.arrays.magnet_array)             size=288
    Skews                 (pyaml.arrays.magnet_array)             size=288
    Sext                  (pyaml.arrays.magnet_array)             size=180
    QForTune              (pyaml.arrays.magnet_array)             size=124
    .

tool:
    Access: accelerator.<mode>.tool.get("<name>")
    BBA-BPM_C04-04 (pyaml.tuning_tools.bba)
    BBA2-BPM_C04-04 (pyaml.tuning_tools.bba2)
    CHROMATICITY_MONITOR (pyaml.tuning_tools.chromaticity_monitor)
    DEFAULT_TUNE_CORRECTION (pyaml.tuning_tools.tune)
    DEFAULT_TUNE_RESPONSE_MATRIX (pyaml.tuning_tools.tune_response_matrix)
    DEFAULT_CHROMATICITY_RESPONSE_MATRIX (pyaml.tuning_tools.chromaticity_response_matrix)
    DEFAULT_CHROMATICITY_CORRECTION (pyaml.tuning_tools.chromaticity)
    DEFAULT_ORBIT_CORRECTION (pyaml.tuning_tools.orbit)
    DEFAULT_ORBIT_RESPONSE_MATRIX (pyaml.tuning_tools.orbit_response_matrix)
    DEFAULT_DISPERSION (pyaml.tuning_tools.dispersion)
    .

diagnostic:
    Access: accelerator.<mode>.diagnostic.get("<name>")
    BETATRON_TUNE (pyaml.diagnostics.tune_monitor)
    ."""


def test_load_conf_with_code():
    parent_folder = Path(__file__).parent
    config_path = parent_folder.joinpath("config", "EBSOrbit.yaml").resolve()

    sr: Accelerator = Accelerator.load(config_path)
    str_repr = str(sr.yellow_pages)
    print(str_repr)
    assert ebs_orbit_str_repr == str_repr
