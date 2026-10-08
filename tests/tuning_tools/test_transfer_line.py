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
        orm_h[8, :], [1.49746082, 3.11487458, 10.60522905, -0.84014865, -19.27774502, -14.92314963, 1.29287711, 1.60223207]
    )
    assert numpy.allclose(
        orm_v[8, :], [10.95115436, 10.56436269, 16.43975007, 32.48697172, 12.7218589, 10.31009581, 10.46821268, 2.60568252]
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
    assert numpy.allclose(numpy.std(orbit.get(), axis=0), [1.78601145e-05, 3.57671504e-05])

    tl2.design.tool.orbit.correct()
    tl2.design.tool.orbit.correct()

    assert numpy.allclose(numpy.std(orbit.get(), axis=0), [7.50786048e-07, 7.26005222e-07])

    assert numpy.allclose(orbit.get()[2], tl2.design.diagnostic.bpm.get("BPM_QD5").positions.get())
