"""Holder interface for diagnostics."""

from typing import TYPE_CHECKING

from ...arrays.element_array import ElementArray
from ...diagnostics.tune_monitor import BetatronTuneMonitor
from ..element import Element, __pyaml_repr__
from ..exception import PyAMLException
from .sub_holders import BPMHolder, BPMsHolder

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
    bpm, bpms
        Single BPM by name, or a named BPM array.
    betatron_tune
        Betatron tune monitor configured as ``BETATRON_TUNE``, the default, validated
        against its expected class.

    Methods
    -------
    get(name=None)
        Return a named diagnostic, or all configured diagnostics when no name is given.

    Notes
    -----
    :meth:`ElementHolder.get_betatron_tune_monitor
    <pyaml.common.holders.element_holder.ElementHolder.get_betatron_tune_monitor>` stays
    available as the named, untyped lookup. This holder adds the default-name,
    type-validated convenience property.

    Examples
    --------
    >>> default_tune_monitor = sr.live.diagnostic.betatron_tune
    >>> measured_tune = default_tune_monitor.tune.get()
    >>> spare_tune_monitor = sr.live.diagnostic.get("SPARE_BETATRON_TUNE_MONITOR")
    >>> all_diagnostics = sr.live.diagnostic.get()
    >>> bpm = sr.live.diagnostic.bpm.get("BPM01")
    >>> bpms = sr.live.diagnostic.bpms.get("BPMS")
    """

    def __init__(self, peer: "ElementHolder"):
        """
        Initialize a diagnostic holder for an element holder.
        """
        self._peer = peer
        self._bpm_holder = BPMHolder(peer)
        self._bpms_holder = BPMsHolder(peer)

    @property
    def bpm(self) -> BPMHolder:
        """Return the bpm."""
        return self._bpm_holder

    @property
    def bpms(self) -> BPMsHolder:
        """Return the bpms."""
        return self._bpms_holder

    def get(self, name: str = None) -> "Element | ElementArray":
        """
        Return a named diagnostic, or all configured diagnostics when no name is given.

        Parameters
        ----------
        name : str, optional
            Name of the diagnostic to look up, as declared in the configuration. When
            omitted, every configured diagnostic is returned instead.

        Returns
        -------
        Element or ElementArray
            The diagnostic registered under ``name``, or an
            :class:`~pyaml.arrays.element_array.ElementArray` holding every configured
            diagnostic, in insertion order, when ``name`` is omitted.

        Raises
        ------
        PyAMLException
            If ``name`` is given and no diagnostic is registered under it.
        """
        if name is None:
            return ElementArray("", list(self._peer._DIAG.values()))
        return self._peer._get_diagnostic(name)

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
        obj = self._peer.get_betatron_tune_monitor(name)
        if not isinstance(obj, BetatronTuneMonitor):
            raise PyAMLException(f"{name}: BetatronTuneMonitor expected but got {type(obj).__name__}")
        return obj

    def __repr__(self):
        return __pyaml_repr__(self)
