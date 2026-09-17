import at
import pytest

from pyaml import PyAMLException
from pyaml.accelerator import Accelerator
from pyaml.lattice.attribute_linker import (
    PyAtAttributeElementsLinker,
    PyAtAttributeIdentifier,
)
from pyaml.lattice.simulator import Simulator

# -----------------------
# Dummy PyAML Element
# -----------------------


class DummyPyAMLElement:
    """Minimal stand-in for a PyAML Element: only provides .name and .lattice_names."""

    def __init__(self, name: str, lattice_names: str | None = None):
        self._name = name
        self._lattice_names = lattice_names

    def get_name(self) -> str:
        return self._name

    def get_lattice_names(self) -> str | None:
        return self._lattice_names


def test_conf_with_linker():
    sr: Accelerator = Accelerator.load("tests/config/sr-attribute-linker.yaml")
    assert sr is not None
    magnet = sr.design.magnet.get("SH1A-C01-H")
    assert magnet is not None


# -----------------------
# PyAtAttributeElementsLinker tests
# -----------------------


def test_attribute_identifier_from_pyaml_name(lattice_with_custom_attr):
    """We bind to AT element attribute 'Tag';
    identifier value comes from PyAML element .name"""
    linker = PyAtAttributeElementsLinker(attribute_name="Tag")
    linker.set_lattice(lattice_with_custom_attr)
    pyaml_elem = DummyPyAMLElement(name="QF")  # identifier="QF"
    ident = linker.get_element_identifier(pyaml_elem)
    assert isinstance(ident, PyAtAttributeIdentifier)
    assert ident.attribute_name == "Tag"
    assert ident.identifier == "QF"


def test_attribute_get_at_elements_all_matches(lattice_with_custom_attr):
    linker = PyAtAttributeElementsLinker(attribute_name="Tag")
    linker.set_lattice(lattice_with_custom_attr)
    ident = PyAtAttributeIdentifier("Tag", "QF")
    matches = linker.get_at_elements(ident)
    # There are two elements with Tag == "QF"
    assert len(matches) == 2
    assert all(getattr(e, "Tag", None) == "QF" for e in matches)


def test_attribute_get_at_element_first_match(lattice_with_custom_attr):
    linker = PyAtAttributeElementsLinker(attribute_name="Tag")
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
    linker = PyAtAttributeElementsLinker(attribute_name="Tag")
    linker.set_lattice(lattice_with_custom_attr)
    ident = PyAtAttributeIdentifier("Tag", "ZZ")
    with pytest.raises(PyAMLException):
        _ = linker.get_at_elements(ident)
    with pytest.raises(PyAMLException):
        _ = linker.get_at_element(ident)


def test_attribute_multiple_identifiers_accumulate(lattice_with_custom_attr):
    linker = PyAtAttributeElementsLinker(attribute_name="Tag")
    linker.set_lattice(lattice_with_custom_attr)
    ids = [PyAtAttributeIdentifier("Tag", "QF"), PyAtAttributeIdentifier("Tag", "QD")]
    res = linker.get_at_elements(ids)
    tags = [getattr(e, "Tag", None) for e in res]
    assert tags.count("QF") == 2 and tags.count("QD") == 1
    assert len(res) == 3


def check_index(ring, elts, indices):
    for idx, e in enumerate(elts):
        assert ring.index(e) == indices[idx]


# Ring indices of the QF1E / QF1I quadrupoles of sr/lattices/ebs-original-names.mat
QF1E_INDICES = [
    140, 290, 424, 576, 712, 848, 982, 1116, 1250, 1384, 1525, 1662, 1803, 1937, 2078, 2212,
    2348, 2482, 2616, 2762, 2898, 3046, 3182, 3316, 3452, 3593, 3732, 3873, 4009, 4150, 4286,
]  # fmt: skip
QF1E_ALL_INDICES = QF1E_INDICES + [4430]


@pytest.mark.parametrize("config", ["tests/config/EBSNames.yaml", "tests/config/EBSNames-linker.yaml"])
def test_various_naming_addressing(config):
    """lattice_names selectors give the same elements with and without a linker."""
    sr = Accelerator.load(config, ignore_external=True)
    ring = sr.design.get_lattice()

    elts = sr.design.magnet.get("QF1E").strength._elements
    assert len(elts) == 31
    check_index(ring, elts, QF1E_INDICES)

    elts = sr.design.magnet.get("QF1E-ALL").strength._elements
    assert len(elts) == 32
    check_index(ring, elts, QF1E_ALL_INDICES)

    elts = sr.design.magnet.get("QF1E-C05").strength._elements
    assert len(elts) == 1
    check_index(ring, elts, [290])

    elts = sr.design.magnet.get("QF1E-C04-C05-C06").strength._elements
    assert len(elts) == 3
    check_index(ring, elts, [140, 290, 424])

    elts = sr.design.magnet.get("QF1E-C04-C05-C06-2").strength._elements
    assert len(elts) == 3
    check_index(ring, elts, [140, 290, 424])

    elts = sr.design.magnet.get("QF1E-C04-C05-C06-3").strength._elements
    assert len(elts) == 3
    check_index(ring, elts, [140, 290, 424])


# -----------------------
# lattice_names selectors with a linker
# -----------------------


@pytest.fixture
def simulator_with_tag_linker(lattice_with_custom_attr, tmp_path) -> Simulator:
    """Simulator on the 'Tag' lattice: D1(Tag=D1) QF(Tag=QF) QF2(Tag=QF) QD(Tag=QD)."""
    lattice_file = tmp_path / "tag_lattice.m"
    at.save_m(lattice_with_custom_attr, str(lattice_file))
    return Simulator(name="design", lattice=str(lattice_file), linker=PyAtAttributeElementsLinker(attribute_name="Tag"))


def _tags(elements):
    return [getattr(e, "Tag", None) for e in elements]


def test_linker_without_lattice_names_uses_element_name(simulator_with_tag_linker):
    elts = simulator_with_tag_linker.get_at_elems(DummyPyAMLElement("QF"))
    assert _tags(elts) == ["QF", "QF"]


def test_linker_lattice_names_list(simulator_with_tag_linker):
    sim = simulator_with_tag_linker
    assert _tags(sim.get_at_elems(DummyPyAMLElement("anything", "list(QF)"))) == ["QF", "QF"]
    assert _tags(sim.get_at_elems(DummyPyAMLElement("anything", "list(QF,QD)"))) == ["QF", "QF", "QD"]


def test_linker_lattice_names_indices(simulator_with_tag_linker):
    sim = simulator_with_tag_linker
    ring = sim.ring
    assert sim.get_at_elems(DummyPyAMLElement("x", "QF@1")) == [ring[2]]
    assert sim.get_at_elems(DummyPyAMLElement("x", "QF@0,1")) == [ring[1], ring[2]]
    assert sim.get_at_elems(DummyPyAMLElement("x", "QF#0..2")) == [ring[1], ring[2]]
    # Empty name: direct indexing in the whole ring
    assert sim.get_at_elems(DummyPyAMLElement("x", "@3")) == [ring[3]]
    assert sim.get_at_elems(DummyPyAMLElement("x", "#1..3")) == [ring[1], ring[2]]


def test_linker_lattice_names_share_lattice_element(simulator_with_tag_linker):
    """Two PyAML elements with different names can drive the same PyAT element."""
    sim = simulator_with_tag_linker
    main = sim.get_at_elems(DummyPyAMLElement("QD"))
    coil = sim.get_at_elems(DummyPyAMLElement("QD_H", "list(QD)"))
    assert main == coil == [sim.ring[3]]


def test_linker_lattice_names_errors(simulator_with_tag_linker):
    sim = simulator_with_tag_linker
    with pytest.raises(PyAMLException):
        sim.get_at_elems(DummyPyAMLElement("x", "list(ZZ)"))
    with pytest.raises(PyAMLException):
        sim.get_at_elems(DummyPyAMLElement("x", "ZZ@0"))
    with pytest.raises(PyAMLException):
        sim.get_at_elems(DummyPyAMLElement("x", "QF@5"))
