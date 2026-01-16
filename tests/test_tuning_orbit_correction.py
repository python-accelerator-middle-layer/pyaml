import logging
from pathlib import Path

import numpy as np

from pyaml.accelerator import Accelerator
from pyaml.configuration.factory import Factory
from pyaml.tuning_tools.orbit import ConfigModel as Orbit_ConfigModel
from pyaml.tuning_tools.orbit import Orbit


def test_tuning_orm():
    logging.getLogger("pyaml.tuning_tools").setLevel(logging.WARNING)

    parent_folder = Path(__file__).parent
    config_path = parent_folder.joinpath("config", "EBSOrbit.yaml").resolve()
    sr = Accelerator.load(config_path)
    element_holder = sr.design

    orbit = Orbit(
        element_holder=element_holder,
        cfg=Orbit_ConfigModel(
            bpm_array_name="BPM",
            hcorr_array_name="HCorr",
            vcorr_array_name="VCorr",
            singular_values=162,
            response_matrix_file=str(
                parent_folder.joinpath("config", "ideal_orm_disp.json").resolve()
            ),
        ),
    )

    ## generate some orbit
    np.random.seed(42)
    std_kick = 1e-6
    hcorr = element_holder.get_magnets("HCorr")
    vcorr = element_holder.get_magnets("VCorr")
    bpms = element_holder.get_bpms("BPM")

    # mangle orbit
    hcorr.strengths.set(
        hcorr.strengths.get() + std_kick * np.random.normal(size=len(hcorr))
    )
    vcorr.strengths.set(
        vcorr.strengths.get() + std_kick * np.random.normal(size=len(vcorr))
    )

    positions_bc = bpms.positions.get()
    std_bc = np.std(positions_bc, axis=0)
    assert np.isclose(std_bc[0], 6.667876984477872e-05, rtol=0, atol=1e-14)
    assert np.isclose(std_bc[1], 4.596925753632764e-05, rtol=0, atol=1e-14)

    orbit.correct(reference=None)

    positions_ac = bpms.positions.get()
    std_ac = np.std(positions_ac, axis=0)
    assert np.isclose(std_ac[0], 5.041856471193712e-07, rtol=0, atol=1e-14)
    assert np.isclose(std_ac[1], 4.789269566479167e-07, rtol=0, atol=1e-14)

    Factory.clear()
