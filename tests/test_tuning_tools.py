import numpy as np

from pyaml.accelerator import Accelerator
from pyaml.common.constants import Action


def callback(action: Action, data: dict):
    print(f"{action}, data:{data}")
    return True


def test_tune_tool():
    sr = Accelerator.load("tests/config/EBSTune.yaml", use_fast_loader=True)
    sr.design.get_lattice().disable_6d()
    sr.design.trm.measure(callback=callback)
    sr.design.trm.save("tunemat.json")
    sr.design.tune.load("tunemat.json")
    sr.design.tune.set([0.17, 0.32], iter=2)
    tune = sr.design.tune.readback()
    assert np.abs(tune[0] - 0.17) < 1e-5
    assert np.abs(tune[1] - 0.32) < 1e-5


def test_tune_add():
    sr = Accelerator.load("tests/config/EBSTune.yaml", use_fast_loader=True)
    sr.design.get_lattice().disable_6d()
    sr.design.tune.load("tunemat.json")
    tune_initial = sr.design.tune.readback()
    dtune = np.array([0.01, -0.01])
    sr.design.tune.add(dtune)
    tune = sr.design.tune.readback()
    np.testing.assert_allclose(tune - tune_initial, dtune, atol=1e-5)


def test_chroma_tool():
    sr: Accelerator = Accelerator.load("tests/config/EBSOrbit.yaml", use_fast_loader=True)
    sr.design.get_lattice().enable_6d()
    sr.design.chromaticity.set([8.0, 5.0], iter=2)
    QpAT = sr.design.get_lattice().get_chrom()[:-1]
    Qp = sr.design.chromaticity.readback()
    assert np.abs(Qp[0] - 8.0) < 1e-3
    assert np.abs(Qp[1] - 5.0) < 1e-3
    assert np.abs(QpAT[0] - 8.0) < 1e-2
    assert np.abs(QpAT[1] - 5.0) < 1e-2


def test_chroma_add():
    sr: Accelerator = Accelerator.load("tests/config/EBSOrbit.yaml", use_fast_loader=True)
    sr.design.get_lattice().enable_6d()
    chromaAT = sr.design.get_lattice().get_chrom()[:-1]
    sr.design.chromaticity.add([0.5, 0.4])
    chromaAT2 = sr.design.get_lattice().get_chrom()[:-1]
    chromaDiff = chromaAT2 - chromaAT
    assert np.abs(chromaDiff[0] - 0.5) < 5e-2
    assert np.abs(chromaDiff[1] - 0.4) < 5e-2
