import logging
import tempfile
from pathlib import Path

import numpy as np

from pyaml.accelerator import Accelerator


def test_tuning_orm():
    logging.getLogger("pyaml.tuning_tools").setLevel(logging.WARNING)

    parent_folder = Path(__file__).parent
    config_path = parent_folder.joinpath("..", "config", "EBSOrbit.yaml").resolve()
    sr = Accelerator.load(config_path)
    element_holder = sr.design

    orm = element_holder.tool.orm

    bpms = element_holder.diagnostic.bpms.get("BPM")
    hcorr_names = element_holder.magnets.get("HCorr").names()[:4]
    vcorr_names = element_holder.magnets.get("VCorr").names()[:4]
    orm.measure(corrector_names=hcorr_names + vcorr_names)

    orm_data = orm.get()
    orm_shape = np.array(orm_data["matrix"]).shape
    assert orm_shape == (2 * len(bpms), 8)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", prefix="orm_") as f:
        # save file
        orm.save(save_path=f.name)

        # load saved file
        element_holder.tool.orbit.load(f.name)


def test_orm_block_getters():
    logging.getLogger("pyaml.tuning_tools").setLevel(logging.WARNING)

    parent_folder = Path(__file__).parent
    config_path = parent_folder.joinpath("..", "config", "EBSOrbit.yaml").resolve()
    sr = Accelerator.load(config_path)
    element_holder = sr.design

    orm = element_holder.tool.orm

    hcorr_names = element_holder.magnets.get("HCorr").names()[:2]
    vcorr_names = element_holder.magnets.get("VCorr").names()[:2]
    orm.measure(corrector_names=hcorr_names + vcorr_names)

    data = orm.get()
    assert data is not None
    assert "matrix" in data

    h2h = orm.get_h2h_matrix()
    v2v = orm.get_v2v_matrix()
    h2v = orm.get_h2v_matrix()
    v2h = orm.get_v2h_matrix()

    n_bpms = len(element_holder.diagnostic.bpms.get("BPM"))
    assert len(h2h) == n_bpms  # H observables
    assert len(h2h[0]) == 2  # 2 H correctors
    assert len(v2v) == n_bpms
    assert len(v2v[0]) == 2
    assert len(h2v) == n_bpms
    assert len(h2v[0]) == 2
    assert len(v2h) == n_bpms
    assert len(v2h[0]) == 2
