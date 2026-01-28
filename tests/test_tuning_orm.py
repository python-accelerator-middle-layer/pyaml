import logging
from pathlib import Path

import numpy as np

from pyaml.accelerator import Accelerator
from pyaml.configuration.factory import Factory
from pyaml.tuning_tools.orbit_response_matrix import ConfigModel as ORM_ConfigModel
from pyaml.tuning_tools.orbit_response_matrix import OrbitResponseMatrix


def test_tuning_orm():
    logging.getLogger("pyaml.tuning_tools").setLevel(logging.WARNING)

    parent_folder = Path(__file__).parent
    config_path = parent_folder.joinpath("config", "EBSOrbit.yaml").resolve()
    sr = Accelerator.load(config_path)
    element_holder = sr.design

    orm = element_holder.orm

    bpms = element_holder.get_bpms("BPM")
    hcorr_names = element_holder.get_magnets("HCorr").names()[:4]
    vcorr_names = element_holder.get_magnets("VCorr").names()[:4]
    orm.measure(corrector_names=hcorr_names + vcorr_names)

    orm_data = orm.get()
    orm_shape = np.array(orm_data["matrix"]).shape
    assert orm_shape == (2 * len(bpms), 8)

    Factory.clear()
