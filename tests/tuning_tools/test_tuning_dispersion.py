import logging
from pathlib import Path

from pyaml.accelerator import Accelerator
from pyaml.common.constants import Action


def test_tuning_orm():
    logging.getLogger("pyaml.tuning_tools").setLevel(logging.WARNING)

    parent_folder = Path(__file__).parent
    config_path = parent_folder.joinpath("..", "config", "EBSOrbit.yaml").resolve()
    sr = Accelerator.load(config_path)
    element_holder = sr.design

    dispersion = element_holder.tool.dispersion

    # for callback testing
    actions = []

    def callback(action, data):
        actions.append(action)
        return True

    dispersion.measure(callback=callback)

    # check callback actions:
    assert Action.BEFORE_BPM_READING in actions
    assert Action.APPLY in actions
    assert Action.MEASURE in actions
    assert Action.INIT in actions
    assert Action.RESTORE in actions

    dispersion_data = dispersion.get()

    bpms = element_holder.diagnostic.bpms.get("BPM")

    assert len(dispersion_data["frequency_response_x"]) == len(bpms)
    assert len(dispersion_data["frequency_response_y"]) == len(bpms)
