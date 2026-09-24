"""Holder interface for tuning and measurement tools."""

from typing import TYPE_CHECKING

from ...arrays.element_array import ElementArray
from ..element import Element, __pyaml_repr__
from ..exception import PyAMLException
from ..name_matching import is_wildcard, resolve_names

if TYPE_CHECKING:
    from ...tuning_tools.chromaticity import Chromaticity
    from ...tuning_tools.chromaticity_response_matrix import ChromaticityResponseMatrix
    from ...tuning_tools.dispersion import Dispersion
    from ...tuning_tools.orbit import Orbit
    from ...tuning_tools.orbit_response_matrix import OrbitResponseMatrix
    from ...tuning_tools.tune import Tune
    from ...tuning_tools.tune_response_matrix import TuneResponseMatrix
    from .element_holder import ElementHolder


class ToolHolder:
    """
    Provide access to tuning and measurement tools.

    Parameters
    ----------
    peer : 'ElementHolder'
        Parent holder containing the tool store.

    Attributes
    ----------
    tune, chromaticity, orbit, dispersion
        Default tuning tool for each kind, resolved from its ``DEFAULT_...`` name and
        validated against the expected class.
    trm, crm, orm
        Default response-matrix measurement tool for each kind, resolved the same way.

    Methods
    -------
    get(name=None)
        Return a named tool, or all configured tools when no name is given.

    Notes
    -----
    :attr:`ElementHolder.tune <pyaml.common.holders.element_holder.ElementHolder.tune>`,
    ``.trm``, ``.orbit``, ``.orm``, ``.chromaticity``, ``.crm`` and ``.dispersion`` are
    backward-compatible aliases for the corresponding properties here.

    Examples
    --------
    >>> tune_correction = sr.live.tool.tune
    >>> tune_correction.set([0.31, 0.22])
    >>> tune_response = sr.live.tool.trm
    >>> tune_response.measure()
    >>> other_tool = sr.live.tool.get("OTHER_TUNE_CORRECTION")
    >>> all_tools = sr.live.tool.get()
    """

    def __init__(self, peer: "ElementHolder"):
        """
        Initialize a tool holder for an element holder.
        """
        self._peer = peer

    def get(self, name: str = None) -> "Element | ElementArray":
        """
        Return a named tool, or all configured tools when no name is given.

        Parameters
        ----------
        name : str, optional
            Name of the tuning or measurement tool to look up, as declared in the
            configuration. When omitted, every configured tool is returned instead.

        Returns
        -------
        Element or ElementArray
            The tool registered under ``name``, or an :class:`~pyaml.arrays.element_array.ElementArray`
            holding every configured tool, in insertion order, when ``name`` is omitted.

        Raises
        ------
        PyAMLException
            If ``name`` is given and no tool is registered under it.
        """
        if name is None:
            return ElementArray("", list(self._peer._TOOLS.values()))
        return self._peer._get_tool(name)

    def __getitem__(self, key: str | list[str] | tuple[str, ...]) -> "Element | ElementArray":
        """
        Return a tool, or a selection typed as a generic ElementArray.

        Parameters
        ----------
        key : str, list[str] or tuple[str, ...]
            An exact literal name returns the stored tool. An fnmatch
            wildcard, a ``re:``-prefixed regular expression, or a list/tuple
            of such patterns returns an ElementArray of matches (possibly
            empty).

        Returns
        -------
        Element or ElementArray
            The stored tool for an exact literal name, otherwise an
            ElementArray of matches.

        Raises
        ------
        PyAMLException
            If an exact literal name, or a literal entry within a list or
            tuple, does not match any tool, or a ``re:`` pattern is not a
            valid regular expression.
        """
        store = self._peer._TOOLS
        if isinstance(key, str) and not key.startswith(("re:", "~")) and not is_wildcard(key):
            return self._peer._get_tool(key)
        names = resolve_names(store.keys(), key, what="Tool")
        return ElementArray("", [store[n] for n in names])

    def _validate_type(self, name: str, obj: Element, expected_type: type) -> Element:
        """
        Ensure a resolved default tool matches the type its accessor expects.

        Raises
        ------
        PyAMLException
            If ``obj`` is not an instance of ``expected_type``.
        """
        if not isinstance(obj, expected_type):
            raise PyAMLException(f"{name}: {expected_type.__name__} expected but got {type(obj).__name__}")
        return obj

    @property
    def chromaticity(self) -> "Chromaticity":
        """Return the chromaticity tuning tool configured as ``DEFAULT_CHROMATICITY_CORRECTION``."""
        from ...tuning_tools.chromaticity import Chromaticity

        name = "DEFAULT_CHROMATICITY_CORRECTION"
        return self._validate_type(name, self._peer.get_chromaticity_tuning(name), Chromaticity)

    @property
    def crm(self) -> "ChromaticityResponseMatrix":
        """Return the chromaticity response-matrix tool configured as ``DEFAULT_CHROMATICITY_RESPONSE_MATRIX``."""
        from ...tuning_tools.chromaticity_response_matrix import ChromaticityResponseMatrix

        name = "DEFAULT_CHROMATICITY_RESPONSE_MATRIX"
        return self._validate_type(name, self._peer.get_crm_tuning(name), ChromaticityResponseMatrix)

    @property
    def tune(self) -> "Tune":
        """Return the tune correction tool configured as ``DEFAULT_TUNE_CORRECTION``."""
        from ...tuning_tools.tune import Tune

        name = "DEFAULT_TUNE_CORRECTION"
        return self._validate_type(name, self._peer.get_tune_tuning(name), Tune)

    @property
    def trm(self) -> "TuneResponseMatrix":
        """Return the tune response-matrix tool configured as ``DEFAULT_TUNE_RESPONSE_MATRIX``."""
        from ...tuning_tools.tune_response_matrix import TuneResponseMatrix

        name = "DEFAULT_TUNE_RESPONSE_MATRIX"
        return self._validate_type(name, self._peer.get_trm_tuning(name), TuneResponseMatrix)

    @property
    def orbit(self) -> "Orbit":
        """Return the orbit correction tool configured as ``DEFAULT_ORBIT_CORRECTION``."""
        from ...tuning_tools.orbit import Orbit

        name = "DEFAULT_ORBIT_CORRECTION"
        return self._validate_type(name, self._peer.get_orbit_tuning(name), Orbit)

    @property
    def orm(self) -> "OrbitResponseMatrix":
        """Return the orbit response-matrix tool configured as ``DEFAULT_ORBIT_RESPONSE_MATRIX``."""
        from ...tuning_tools.orbit_response_matrix import OrbitResponseMatrix

        name = "DEFAULT_ORBIT_RESPONSE_MATRIX"
        return self._validate_type(name, self._peer.get_orm_tuning(name), OrbitResponseMatrix)

    @property
    def dispersion(self) -> "Dispersion":
        """Return the dispersion tool configured as ``DEFAULT_DISPERSION``."""
        from ...tuning_tools.dispersion import Dispersion

        name = "DEFAULT_DISPERSION"
        return self._validate_type(name, self._peer.get_dispersion_tuning(name), Dispersion)

    def __repr__(self):
        return __pyaml_repr__(self)
