import pytest

from pyaml import PyAMLException

from pyaml.lattice.famname_linker import (
    FamNameElementsLinker,
    FamNameIdentifier,
    ConfigModel as FamNameConfigModel,
)
from pyaml.lattice.attribute_linker import (
    PyAtAttributeElementsLinker,
    PyAtAttributeIdentifier,
    ConfigModel as AttrConfigModel,
)
# -----------------------
# Dummy PyAML Element
# -----------------------

class DummyPyAMLElement:
    """Minimal stand-in for a PyAML Element: only provides .name."""
    def __init__(self, name: str):
        self.name = name


# -----------------------
# FamNameElementsLinker tests
# -----------------------

def test_famname_identifier_from_pyaml_name(lattice_with_famnames):
    linker = FamNameElementsLinker(FamNameConfigModel())
    linker.set_lattice(lattice_with_famnames)
    pyaml_elem = DummyPyAMLElement(name="QF")
    ident = linker.get_element_identifier(pyaml_elem)
    assert isinstance(ident, FamNameIdentifier)
    assert ident.family_name == "QF"   # identifier mirrors Element.name


def test_famname_get_at_elements_all_matches(lattice_with_famnames):
    linker = FamNameElementsLinker()
    linker.set_lattice(lattice_with_famnames)
    ident = FamNameIdentifier("QF")
    matches = linker.get_at_elements(ident)
    assert len(matches) == 2
    assert all(getattr(e, "FamName", None) == "QF" for e in matches)


def test_famname_get_at_element_first_match(lattice_with_famnames):
    linker = FamNameElementsLinker()
    linker.set_lattice(lattice_with_famnames)
    ident = FamNameIdentifier("QF")
    first = linker.get_at_element(ident)
    assert first == lattice_with_famnames[0]
    assert first.FamName == "QF"


def test_famname_no_match_raises(lattice_with_famnames):
    linker = FamNameElementsLinker()
    linker.set_lattice(lattice_with_famnames)
    ident = FamNameIdentifier("QX")  # nonexistent FamName
    with pytest.raises(PyAMLException):
        _ = linker.get_at_elements(ident)
    with pytest.raises(PyAMLException):
        _ = linker.get_at_element(ident)


def test_famname_multiple_identifiers_accumulate(lattice_with_famnames):
    linker = FamNameElementsLinker()
    linker.set_lattice(lattice_with_famnames)
    ids = [FamNameIdentifier("QF"), FamNameIdentifier("QD")]
    res = linker.get_at_elements(ids)
    fams = [e.FamName for e in res]
    assert fams.count("QF") == 2 and fams.count("QD") == 1
    assert len(res) == 3


# -----------------------
# PyAtAttributeElementsLinker tests
# -----------------------

def test_attribute_identifier_from_pyaml_name(lattice_with_custom_attr):
    # We bind to AT element attribute 'Tag'; identifier value comes from PyAML element .name
    linker = PyAtAttributeElementsLinker(AttrConfigModel(attribute_name="Tag"))
    linker.set_lattice(lattice_with_custom_attr)
    pyaml_elem = DummyPyAMLElement(name="QF")   # identifier="QF"
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
