import logging
from pathlib import Path

import numpy as np

from pyaml.accelerator import Accelerator
from pyaml.common.exception import PyAMLConfigException
from pyaml.configuration.factory import Factory


def test_tuning_orbit_correction():
    logging.getLogger("pyaml.tuning_tools").setLevel(logging.WARNING)

    parent_folder = Path(__file__).parent
    config_path = parent_folder.joinpath("config", "EBSOrbit.yaml").resolve()
    sr = Accelerator.load(config_path)
    element_holder = sr.design

    ## generate some orbit
    np.random.seed(42)
    std_kick = 1e-6
    hcorr = element_holder.get_magnets("HCorr")
    vcorr = element_holder.get_magnets("VCorr")
    bpms = element_holder.get_bpms("BPM")

    x, y = bpms.positions.get().T  # get reference orbit
    reference = np.concat((x, y))
    # there should be nothing to correct, but still work
    element_holder.orbit.correct(reference=reference)

    h_strengths = hcorr.strengths.get() + std_kick * np.random.normal(size=len(hcorr))
    v_strengths = vcorr.strengths.get() + std_kick * np.random.normal(size=len(vcorr))

    # mangle orbit
    hcorr.strengths.set(h_strengths)
    vcorr.strengths.set(v_strengths)

    positions_bc = bpms.positions.get()
    std_bc = np.std(positions_bc, axis=0)
    original_H = 6.667876984477872e-05
    original_V = 4.596925753632764e-05
    assert np.isclose(std_bc[0], original_H, rtol=0, atol=1e-14)
    assert np.isclose(std_bc[1], original_V, rtol=0, atol=1e-14)

    element_holder.orbit.correct(reference=None)

    positions_ac = bpms.positions.get()
    std_ac = np.std(positions_ac, axis=0)
    assert np.isclose(std_ac[0], 5.041856471193712e-07, rtol=0, atol=1e-14)
    assert np.isclose(std_ac[1], 4.789269566479167e-07, rtol=0, atol=1e-14)

    # mangle orbit again, test gain_H/gain_V
    hcorr.strengths.set(h_strengths)
    vcorr.strengths.set(v_strengths)
    element_holder.orbit.correct(gain_H=0.5, gain_V=0.1)

    positions_ac = bpms.positions.get()
    std_ac = np.std(positions_ac, axis=0)
    assert np.isclose(std_ac[0], 3.35354284052137e-05, rtol=0, atol=1e-14)
    assert np.isclose(std_ac[1], 4.1339663520424604e-05, rtol=0, atol=1e-14)

    # mangle orbit again, test gain/gain_V
    hcorr.strengths.set(h_strengths)
    vcorr.strengths.set(v_strengths)
    element_holder.orbit.correct(gain=1, gain_V=0.1)

    positions_ac = bpms.positions.get()
    std_ac = np.std(positions_ac, axis=0)
    assert np.isclose(std_ac[0], 5.104224174704558e-07, rtol=0, atol=1e-14)
    assert np.isclose(std_ac[1], 4.1313661790996294e-05, rtol=0, atol=1e-14)

    # mangle orbit again, test singular_values_H
    hcorr.strengths.set(h_strengths)
    vcorr.strengths.set(v_strengths)
    element_holder.orbit.correct(singular_values_H=100)

    positions_ac = bpms.positions.get()
    std_ac = np.std(positions_ac, axis=0)
    assert np.isclose(std_ac[0], 1.3748553578879513e-06, rtol=0, atol=1e-14)
    assert np.isclose(std_ac[1], 4.789939022822169e-07, rtol=0, atol=1e-14)

    # mangle orbit again, test singular_values_V
    hcorr.strengths.set(h_strengths)
    vcorr.strengths.set(v_strengths)
    element_holder.orbit.correct(singular_values_V=50)

    positions_ac = bpms.positions.get()
    std_ac = np.std(positions_ac, axis=0)
    assert np.isclose(std_ac[0], 5.042256801373377e-07, rtol=0, atol=1e-14)
    assert np.isclose(std_ac[1], 2.764901786304611e-06, rtol=0, atol=1e-14)

    # mangle orbit again, test plane=H
    hcorr.strengths.set(h_strengths)
    vcorr.strengths.set(v_strengths)
    element_holder.orbit.correct(plane="H")

    positions_ac = bpms.positions.get()
    std_ac = np.std(positions_ac, axis=0)
    assert np.isclose(std_ac[0], 5.241959150018442e-07, rtol=0, atol=1e-14)
    assert np.isclose(std_ac[1], 4.5907541799723846e-05, rtol=0, atol=1e-14)
    assert np.isclose(std_ac[1], original_V, rtol=1e-2, atol=1e-14)

    # mangle orbit again, test plane=V
    hcorr.strengths.set(h_strengths)
    vcorr.strengths.set(v_strengths)
    element_holder.orbit.correct(plane="V")

    positions_ac = bpms.positions.get()
    std_ac = np.std(positions_ac, axis=0)
    assert np.isclose(std_ac[0], 6.65117255381606e-05, rtol=0, atol=1e-14)
    assert np.isclose(std_ac[1], 4.845815082760313e-07, rtol=0, atol=1e-14)
    assert np.isclose(std_ac[0], original_H, rtol=1e-2, atol=1e-14)

    # mangle orbit again, test reference
    hcorr.strengths.set(h_strengths)
    vcorr.strengths.set(v_strengths)
    reference = np.concatenate((positions_bc[:, 0], positions_bc[:, 1]))
    element_holder.orbit.correct(reference=reference)
    positions_ac = bpms.positions.get()
    std_ac = np.std(positions_ac, axis=0)
    assert np.isclose(std_ac[0], original_H, rtol=0, atol=1e-14)
    assert np.isclose(std_ac[1], original_V, rtol=0, atol=1e-14)

    # no need to mangle orbit again, test reference/plane=H
    element_holder.orbit.correct(reference=reference / 2, plane="H")
    positions_ac = bpms.positions.get()
    std_ac = np.std(positions_ac, axis=0)
    assert np.isclose(std_ac[0], 3.356995564922256e-05, rtol=0, atol=1e-14)
    assert np.isclose(std_ac[1], 4.5936801886172225e-05, rtol=0, atol=1e-14)


def test_tuning_orbit_correction_config():
    # test orbit config
    config_dict = {
        "type": "pyaml.tuning_tools.orbit",
        "bpm_array_name": "BPM",
        "hcorr_array_name": "HCorr",
        "vcorr_array_name": "VCorr",
        "name": "TEST_ORBIT_CORRECTION",
        "singular_values": "162",
        "response_matrix": "file:does_not_exist.json",
    }
    orbit_cor = Factory.depth_first_build(config_dict, ignore_external=False)
    Factory.clear()

    config_dict = {
        "type": "pyaml.tuning_tools.orbit",
        "bpm_array_name": "BPM",
        "hcorr_array_name": "HCorr",
        "vcorr_array_name": "VCorr",
        "name": "TEST_ORBIT_CORRECTION",
        "singular_values_H": "162",
        "response_matrix": "file:does_not_exist.json",
    }
    try:
        orbit_cor = Factory.depth_first_build(config_dict, ignore_external=False)
    except PyAMLConfigException as exc:
        # failed successfully!
        Factory.clear()

    config_dict = {
        "type": "pyaml.tuning_tools.orbit",
        "bpm_array_name": "BPM",
        "hcorr_array_name": "HCorr",
        "vcorr_array_name": "VCorr",
        "name": "TEST_ORBIT_CORRECTION",
        "singular_values_H": "162",
        "singular_values_V": "162",
        "response_matrix": "file:does_not_exist.json",
    }
    orbit_cor = Factory.depth_first_build(config_dict, ignore_external=False)
    Factory.clear()
