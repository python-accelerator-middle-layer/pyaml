import numpy
import pytest

from pyaml.accelerator import Accelerator


def test_transfer_line():
    tl2 = Accelerator.load("tests/config/tl2/tl2.yml")
    tl2.design.tool.orm.measure()
    orm_data = tl2.design.tool.orm.get()
    mat = numpy.array(orm_data["matrix"])

    orm_hv = mat[:9, 8:]
    orm_vh = mat[9:, :8]
    assert numpy.allclose(orm_hv, 0)
    assert numpy.allclose(orm_vh, 0)

    orm_h = mat[:9, :8]
    orm_v = mat[9:, 8:]

    assert numpy.allclose(
        orm_h[8, :], [1.49217029, 3.11318219, 10.60494678, -0.82242986, -19.2814236, -14.92682822, 1.28503979, 1.60584401]
    )
    assert numpy.allclose(
        orm_v[8, :], [10.95203344, 10.56524176, 16.43659334, 32.50321299, 12.72373742, 10.3122307, 10.47365958, 2.61214668]
    )

    tl2.design.tool.orm.save("tl2.json")
    tl2.design.tool.orbit.load("tl2.json")

    # Mangle the orbit
    hcorr = tl2.design.magnets.get("HCORR")
    vcorr = tl2.design.magnets.get("VCORR")
    numpy.random.seed(1)
    std_kick = 1e-6  # rad
    hcorr.strengths.set(hcorr.strengths.get() + std_kick * numpy.random.normal(size=len(hcorr)))
    vcorr.strengths.set(vcorr.strengths.get() + std_kick * numpy.random.normal(size=len(vcorr)))

    orbit = tl2.design.diagnostic.bpms.get("BPMS").positions
    assert numpy.allclose(numpy.std(orbit.get(), axis=0), [1.78288459e-05, 3.57986943e-05])

    tl2.design.tool.orbit.correct()
    tl2.design.tool.orbit.correct()

    assert numpy.allclose(numpy.std(orbit.get(), axis=0), [7.51291713e-07, 7.24545959e-07])

    assert numpy.allclose(orbit.get()[2], tl2.design.diagnostic.bpm.get("BPM_QD5").positions.get())
