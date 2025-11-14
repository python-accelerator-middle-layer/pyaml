from pyaml.accelerator import Accelerator
from pyaml.configuration.factory import Factory
import numpy as np
import pytest

@pytest.mark.parametrize("install_test_package", [{
    "name": "tango-pyaml",
    "path": "tests/dummy_cs/tango-pyaml"
}], indirect=True)
def test_tune(install_test_package):

    sr:Accelerator = Accelerator.load("tests/config/EBSTune.yaml")
    sr.design.get_lattice().disable_6d()

    quadForTuneDesign = sr.design.get_magnets("QForTune")
    quadForTuneLive = sr.live.get_magnets("QForTune")
    tune_monitor = sr.design.get_betatron_tune_monitor("BETATRON_TUNE")
    # Build tune response matrix
    tune = tune_monitor.tune.get()
    print(tune)
    tunemat = np.zeros((len(quadForTuneDesign),2))

    for idx,m in enumerate(quadForTuneDesign):
        str = m.strength.get()
        m.strength.set(str+1e-4)
        dq = tune_monitor.tune.get() - tune
        tunemat[idx] = dq*1e4
        m.strength.set(str)

    # Compute correction matrix
    correctionmat = np.linalg.pinv(tunemat.T)

    # Correct tune
    strs = quadForTuneDesign.strengths.get()
    strs += np.matmul(correctionmat,[0.1,0.05]) # Ask for correction [dqx,dqy]
    quadForTuneDesign.strengths.set(strs)
    newTune = tune_monitor.tune.get()
    diffTune = newTune-tune

    print(diffTune)
    assert( np.abs(diffTune[0]-0.1) < 1e-3 )
    assert( np.abs(diffTune[1]-0.05) < 1e-3 )

    if False:
        # Correct the tune on live (need a Virutal Accelerator)
        quadForTuneLive = sr.live.get_magnets("QForTune")
        strs = quadForTuneLive.strengths.get()
        strs += np.matmul(correctionmat,[0.1,0.05]) # Ask for correction [dqx,dqy]
        quadForTuneLive.strengths.set(strs)


    Factory.clear()
