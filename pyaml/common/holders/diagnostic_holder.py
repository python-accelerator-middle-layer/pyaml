"""Holder interface for diagnostics."""

from typing import TYPE_CHECKING

from ...arrays.element_array import ElementArray
from ...diagnostics.tune_monitor import BetatronTuneMonitor
from ..element import Element, __pyaml_repr__
from ..exception import PyAMLException
from ..name_matching import is_wildcard, resolve_names
from .sub_holders import BPMHolder

if TYPE_CHECKING:
    from .element_holder import ElementHolder


class DiagnosticHolder:
    """
    Provide access to diagnostics.

    Parameters
    ----------
    peer : 'ElementHolder'
        Parent holder containing the diagnostic store.

    Attributes
    ----------
    bpm
        BPMs: ``bpm.get(name)`` for one BPM, ``bpm.get_array(name)`` for a configured BPM array.
    betatron_tune
        Betatron tune monitor configured as ``BETATRON_TUNE``, the default, validated
        against its expected class.

    Methods
    -------
    get(name)
        Return the diagnostic registered under a name.
    get_array()
        Return every configured diagnostic.

    Examples
    --------
    >>> default_tune_monitor = sr.live.diagnostic.betatron_tune
    >>> measured_tune = default_tune_monitor.tune.get()
    >>> spare_tune_monitor = sr.live.diagnostic.get("SPARE_BETATRON_TUNE_MONITOR")
    >>> all_diagnostics = sr.live.diagnostic.get_array()
    >>> bpm = sr.live.diagnostic.bpm.get("BPM01")
    >>> bpms = sr.live.diagnostic.bpm.get_array("BPMS")
    """

    def __init__(self, peer: "ElementHolder"):
        """
        Initialize a diagnostic holder for an element holder.
        """
        self._peer = peer
        self._bpm_holder = BPMHolder(peer)

    @property
    def bpm(self) -> BPMHolder:
        """Return the BPM holder (BPMs and configured BPM arrays)."""
        return self._bpm_holder

    def get(self, name: str) -> Element:
        """
        Return the diagnostic registered under a name.

        Parameters
        ----------
        name : str
            Name of the diagnostic to look up, as declared in the configuration.

        Returns
        -------
        Element
            The diagnostic registered under ``name``.

        Raises
        ------
        PyAMLException
            If no diagnostic is registered under ``name``.
        """
        return self._peer._get_diagnostic(name)

    def get_array(self) -> ElementArray:
        """
        Return every configured diagnostic.

        Returns
        -------
        ElementArray
            New unnamed array holding every configured diagnostic, in insertion order.
        """
        return ElementArray("", list(self._peer._DIAG.values()))

    def __getitem__(self, key: str | list[str] | tuple[str, ...]) -> "Element | ElementArray":
        """
        Return a diagnostic, or a selection typed as a generic ElementArray.

        Parameters
        ----------
        key : str, list[str] or tuple[str, ...]
            An exact literal name returns the stored diagnostic. An fnmatch
            wildcard, a ``re:``-prefixed regular expression, or a list/tuple
            of such patterns returns an ElementArray of matches (possibly
            empty).

        Returns
        -------
        Element or ElementArray
            The stored diagnostic for an exact literal name, otherwise an
            ElementArray of matches.

        Raises
        ------
        PyAMLException
            If an exact literal name, or a literal entry within a list or
            tuple, does not match any diagnostic, or a ``re:`` pattern is
            not a valid regular expression.
        """
        store = self._peer._DIAG
        if isinstance(key, str) and not key.startswith(("re:", "~")) and not is_wildcard(key):
            return self._peer._get_diagnostic(key)
        matched = set(resolve_names(store.keys(), key, what="Diagnostic"))
        return ElementArray("", [v for n, v in store.items() if n in matched])

    @property
    def betatron_tune(self) -> BetatronTuneMonitor:
        """
        Return the betatron tune monitor configured as ``BETATRON_TUNE``.

        Returns
        -------
        BetatronTuneMonitor
            Betatron tune monitor registered under ``BETATRON_TUNE``.

        Raises
        ------
        PyAMLException
            If no diagnostic is registered under ``BETATRON_TUNE``, or if it is not a
            :class:`~pyaml.diagnostics.tune_monitor.BetatronTuneMonitor`.
        """
        name = "BETATRON_TUNE"
        obj = self.get(name)
        if not isinstance(obj, BetatronTuneMonitor):
            raise PyAMLException(f"{name}: BetatronTuneMonitor expected but got {type(obj).__name__}")
        return obj

    def __repr__(self):
        return __pyaml_repr__(self)
