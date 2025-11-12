from abc import ABCMeta, abstractmethod
from typing import Iterable

import at
from at import Lattice
from pydantic import BaseModel, ConfigDict

from pyaml import PyAMLException
from pyaml.common.element import Element


class LinkerConfigModel(BaseModel):
    """Base configuration model for linker definitions.

    This class defines the configuration structure used to instantiate
    a specific linking strategy. Each concrete implementation of a
    `LatticeElementsLinker` may define its own subclass extending this model
    to include additional configuration parameters.

    Attributes
    ----------
    model_config : ConfigDict
        Pydantic configuration allowing arbitrary field types and forbidding
        unexpected extra keys.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")


class LinkerIdentifier(metaclass=ABCMeta):
    """Abstract base class for identifiers used to match PyAML and PyAT elements.

    The identifier acts as an intermediate representation between the PyAML
    configuration and the PyAT lattice. Its exact structure depends on the
    linking strategy (e.g., family name, element index, or user-defined tag).

    Subclasses should define the fields and logic necessary to represent
    a unique reference to one or more PyAT elements.
    """
    pass


class LatticeElementsLinker(metaclass=ABCMeta):
    """Abstract base class defining the interface for PyAT–PyAML element linking.

    Implementations of this class define how PyAML elements are matched
    to PyAT elements based on a given linking strategy (e.g., by family name,
    by index, or by a custom attribute).

    Parameters
    ----------
    linker_config_model : LinkerConfigModel
        The configuration model for the linking strategy.

    Attributes
    ----------
    lattice : at.Lattice
        Reference to the PyAT lattice handled by this linker.
    """

    def __init__(self, linker_config_model:LinkerConfigModel):
        self.linker_config_model = linker_config_model
        self.lattice:Lattice = None

    def set_lattice(self, lattice:Lattice):
        self.lattice = lattice

    @abstractmethod
    def _test_at_element(self, identifier: LinkerIdentifier, element:at.Element) -> bool:
        pass

    @abstractmethod
    def get_element_identifier(self, element:Element) -> LinkerIdentifier:
        pass

    def _iter_matches(self, identifier: LinkerIdentifier) -> Iterable[at.Element]:
        """Yield all elements in the lattice whose matches the identifier."""
        for elem in self.lattice:
            if self._test_at_element(identifier, elem):
                yield elem

    def get_at_elements(self,element_id:LinkerIdentifier|list[LinkerIdentifier]) -> list[at.Element]:
        """Return a list of PyAT elements matching the given identifiers.

        This method should resolve one or multiple PyAML identifiers
        into their corresponding PyAT elements according to the specific
        linking strategy implemented.

        Parameters
        ----------
        element_id : LinkerIdentifier or list of LinkerIdentifier
            One or several identifiers describing which PyAT elements
            to retrieve.

        Returns
        -------
        list of at.Element
            The list of matching PyAT elements found in the lattice.

        Raises
        ------
        PyAMLException
            If no element matches the given identifier(s).
        """
        if isinstance(element_id, LinkerIdentifier):
            identifiers = [element_id]
        else:
            identifiers = element_id

        results: list[at.Element] = []
        for ident in identifiers:
            results.extend(self._iter_matches(ident))

        if not results:
            raise PyAMLException(
                f"No PyAT elements found for identifier(s): "
                f"{', '.join(i.__repr__() for i in identifiers)}"
            )
        return results

    def get_at_element(self, element_id:LinkerIdentifier) -> at.Element:
        """Return a single PyAT element matching the given identifier.

        Parameters
        ----------
        element_id : LinkerIdentifier
            Identifier describing the PyAT element to retrieve.

        Returns
        -------
        at.Element
            The PyAT element matching the identifier.

        Raises
        ------
        PyAMLException
            If no element matches the identifier.
        """
        for elem in self._iter_matches(element_id):
            return elem
        raise PyAMLException(f"No PyAT element found for FamName: {element_id.__repr__()}")