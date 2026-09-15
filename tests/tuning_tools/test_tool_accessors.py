from pyaml.accelerator import Accelerator


def test_tuning_tools_expose_configured_elements():
    sr = Accelerator.load(
        "tests/config/EBSOrbit.yaml",
        ignore_external=True,
        include_locations=False,
    )
    design = sr.design

    tune_monitor = design.get_betatron_tune_monitor("BETATRON_TUNE")
    quadrupoles = design.magnets.get("QForTune")
    assert design.tune.tune_monitor is tune_monitor
    assert design.tune.quadrupoles is quadrupoles
    assert design.trm.tune_monitor is tune_monitor
    assert design.trm.quadrupoles is quadrupoles

    chromaticity_monitor = design.get_chromaticity_monitor("CHROMATICITY_MONITOR")
    sextupoles = design.magnets.get("Sext")
    assert design.chromaticity.chromaticity_monitor is chromaticity_monitor
    assert design.chromaticity.sextupoles is sextupoles
    assert design.crm.chromaticity_monitor is chromaticity_monitor
    assert design.crm.sextupoles is sextupoles

    bpms = design.bpms.get("BPM")
    rf_plant = design.rf.get("DEFAULT_RF_PLANT")
    assert chromaticity_monitor.tune_monitor is tune_monitor
    assert chromaticity_monitor.bpms is bpms
    assert chromaticity_monitor.rf_plant is rf_plant
    assert design.dispersion.bpms is bpms
    assert design.dispersion.rf_plant is rf_plant

    hcorrectors = design.magnets.get("HCorr")
    vcorrectors = design.magnets.get("VCorr")
    assert design.orbit.bpms is bpms
    assert design.orbit.hcorrectors is hcorrectors
    assert design.orbit.vcorrectors is vcorrectors
    assert design.orbit.correctors.names() == hcorrectors.names() + vcorrectors.names()
    assert design.orbit.rf_plant is rf_plant
    assert design.orm.bpms is bpms
    assert design.orm.hcorrectors is hcorrectors
    assert design.orm.vcorrectors is vcorrectors

    for name in ("BBA-BPM_C04-04", "BBA2-BPM_C04-04"):
        bba = design.get_bba(name)
        assert bba.bpms is bpms
        assert bba.bpm is design.bpm.get("BPM_C04-04")
        assert bba.hcorrector is design.magnet.get("SF2E-C02-H")
        assert bba.vcorrector is design.magnet.get("SD1A-C26-V")
        assert bba.quadrupole is design.magnet.get("QF6B-C04")

    assert design.get_bba("BBA2-BPM_C04-04").tune_correction is design.tune
