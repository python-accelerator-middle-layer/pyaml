import pytest

from pyaml import PyAMLException
from pyaml.accelerator import Accelerator
from pyaml.lattice.attribute_linker import (
    ConfigModel as AttrConfigModel,
)
from pyaml.lattice.attribute_linker import (
    PyAtAttributeElementsLinker,
    PyAtAttributeIdentifier,
)

# -----------------------
# Dummy PyAML Element
# -----------------------


class DummyPyAMLElement:
    """Minimal stand-in for a PyAML Element: only provides .name."""

    def __init__(self, name: str):
        self._name = name

    def get_name(self) -> str:
        return self._name


def test_conf_with_linker():
    sr: Accelerator = Accelerator.load("tests/config/sr-attribute-linker.yaml")
    assert sr is not None
    magnet = sr.design.get_magnet("SH1A-C01-H")
    assert magnet is not None


# -----------------------
# PyAtAttributeElementsLinker tests
# -----------------------


def test_attribute_identifier_from_pyaml_name(lattice_with_custom_attr):
    """We bind to AT element attribute 'Tag';
    identifier value comes from PyAML element .name"""
    linker = PyAtAttributeElementsLinker(AttrConfigModel(attribute_name="Tag"))
    linker.set_lattice(lattice_with_custom_attr)
    pyaml_elem = DummyPyAMLElement(name="QF")  # identifier="QF"
    ident = linker.get_element_identifier(pyaml_elem)
    assert isinstance(ident, PyAtAttributeIdentifier)
    assert ident.attribute_name == "Tag"
    assert ident.identifier == "QF"


def test_attribute_get_at_elements_all_matches(lattice_with_custom_attr):
    linker = PyAtAttributeElementsLinker(AttrConfigModel(attribute_name="Tag"))
    linker.set_lattice(lattice_with_custom_attr)
    ident = PyAtAttributeIdentifier("Tag", "QF")
    matches = linker.get_at_elements(ident)
    # There are two elements with Tag == "QF"
    assert len(matches) == 2
    assert all(getattr(e, "Tag", None) == "QF" for e in matches)


def test_attribute_get_at_element_first_match(lattice_with_custom_attr):
    linker = PyAtAttributeElementsLinker(AttrConfigModel(attribute_name="Tag"))
    linker.set_lattice(lattice_with_custom_attr)
    ident = PyAtAttributeIdentifier("Tag", "QD")
    first = linker.get_at_element(ident)
    assert getattr(first, "Tag", None) == "QD"
    # Ensure it's the first with Tag == QD in lattice order
    for e in lattice_with_custom_attr:
        if getattr(e, "Tag", None) == "QD":
            assert first is e
            break


def test_attribute_no_match_raises(lattice_with_custom_attr):
    linker = PyAtAttributeElementsLinker(AttrConfigModel(attribute_name="Tag"))
    linker.set_lattice(lattice_with_custom_attr)
    ident = PyAtAttributeIdentifier("Tag", "ZZ")
    with pytest.raises(PyAMLException):
        _ = linker.get_at_elements(ident)
    with pytest.raises(PyAMLException):
        _ = linker.get_at_element(ident)


def test_attribute_multiple_identifiers_accumulate(lattice_with_custom_attr):
    linker = PyAtAttributeElementsLinker(AttrConfigModel(attribute_name="Tag"))
    linker.set_lattice(lattice_with_custom_attr)
    ids = [PyAtAttributeIdentifier("Tag", "QF"), PyAtAttributeIdentifier("Tag", "QD")]
    res = linker.get_at_elements(ids)
    tags = [getattr(e, "Tag", None) for e in res]
    assert tags.count("QF") == 2 and tags.count("QD") == 1
    assert len(res) == 3


def check_index(ring, elts, indices):
    for idx, e in enumerate(elts):
        assert ring.index(e) == indices[idx]


def test_various_naming_addressing():
    sr = Accelerator.load("tests/config/EBSNames.yaml", ignore_external=True)
    ring = sr.design.get_lattice()

    elts = sr.design.get_magnet("QF1E").strength._RWStrengthScalar__elements
    assert len(elts) == 31
    check_index(
        ring,
        elts,
        [
            140,
            290,
            424,
            576,
            712,
            848,
            982,
            1116,
            1250,
            1384,
            1525,
            1662,
            1803,
            1937,
            2078,
            2212,
            2348,
            2482,
            2616,
            2762,
            2898,
            3046,
            3182,
            3316,
            3452,
            3593,
            3732,
            3873,
            4009,
            4150,
            4286,
        ],
    )

    elts = sr.design.get_magnet("QF1E-ALL").strength._RWStrengthScalar__elements
    assert len(elts) == 32
    check_index(
        ring,
        elts,
        [
            140,
            290,
            424,
            576,
            712,
            848,
            982,
            1116,
            1250,
            1384,
            1525,
            1662,
            1803,
            1937,
            2078,
            2212,
            2348,
            2482,
            2616,
            2762,
            2898,
            3046,
            3182,
            3316,
            3452,
            3593,
            3732,
            3873,
            4009,
            4150,
            4286,
            4430,
        ],
    )

    elts = sr.design.get_magnet("QF1E-C05").strength._RWStrengthScalar__elements
    assert len(elts) == 1
    check_index(ring, elts, [290])

    elts = sr.design.get_magnet("QF1E-C04-C05-C06").strength._RWStrengthScalar__elements
    assert len(elts) == 3
    check_index(ring, elts, [140, 290, 424])

    elts = sr.design.get_magnet(
        "QF1E-C04-C05-C06-2"
    ).strength._RWStrengthScalar__elements
    assert len(elts) == 3
    check_index(ring, elts, [140, 290, 424])

    elts = sr.design.get_magnet(
        "QF1E-C04-C05-C06-3"
    ).strength._RWStrengthScalar__elements
    assert len(elts) == 3
    check_index(ring, elts, [140, 290, 424])
