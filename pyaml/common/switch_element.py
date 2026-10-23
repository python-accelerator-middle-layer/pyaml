"""Switchable accelerator functionality without a required lattice counterpart."""

import copy
from typing import TYPE_CHECKING, Self

from ..validation import DynamicValidation, register_schema
from .abstract import BinaryState
from .element import Element
from .exception import PyAMLException

if TYPE_CHECKING:
    from .holders.element_holder import ElementHolder

PYAMLCLASS = "SwitchElement"


@register_schema
class SwitchElement(Element, DynamicValidation):
    """
    Enable or disable accelerator functionality through one boolean channel.

    Parameters
    ----------
    name : str
        Unique element name, for example ``SOFB`` or ``FOFB``.
    device : str
        Opaque backend reference to one writable boolean channel. Status is
        read from that channel's actual readback, not its requested setpoint.
        Simulator modes do not resolve this reference.
    description : str | None, optional
        Human-readable description of the functionality.

    Notes
    -----
    Control-system operations delegate waiting and timeouts to the backend,
    then verify boolean readback with VALID quality. Numeric 0/1 states are
    not accepted; Python and NumPy boolean scalars are supported. Non-VALID
    quality, including CHANGING, raises an error. Construction and attachment
    never initialize live hardware.

    Each simulator attachment starts disabled and maintains independent state
    without looking up or modifying a lattice element. This element does not
    implement measurement preparation or automatic state restoration.

    Configuration
    -------------
    .. code-block:: yaml

        - class: pyaml.common.switch_element.SwitchElement
          name: SOFB
          device: SOFB_ENABLED
          description: Slow orbit feedback

    Examples
    --------
    With this element configured in an accelerator named ``sr``:

    .. code-block:: python

        feedback = sr.live["SOFB"]
        feedback.disable()
        assert feedback.is_enabled() is False
        feedback.enable()

        simulated_feedback = sr.design["SOFB"]
        assert simulated_feedback.is_enabled() is False
        simulated_feedback.enable()  # Does not affect live hardware or the lattice.
    """

    def __init__(self, name: str, device: str, description: str | None = None):
        """Initialize the element configuration without accessing hardware."""
        super().__init__(name=name, description=description)
        self.device = device
        self._state: BinaryState | None = None

    def attach(self, peer: "ElementHolder", state: BinaryState) -> Self:
        """
        Return a copy bound to a peer and its boolean state interface.

        Parameters
        ----------
        peer : ElementHolder
            Control system or simulator owning this runtime element.
        state : BinaryState
            Boolean state interface owned by this attachment.

        Returns
        -------
        Self
            Attached copy; the original configuration remains unattached.
        """
        obj = copy.copy(self)
        obj._state = state
        obj._peer = peer
        return obj

    def _binding(self) -> BinaryState:
        if self._state is None:
            raise PyAMLException(f"{self.name} has no attached switch channel")
        return self._state

    def _set_enabled(self, enabled: bool) -> None:
        self._binding().set_and_wait(enabled)
        if self.is_enabled() is not enabled:
            raise PyAMLException(f"{self.name}: readback did not confirm enabled={enabled}")

    def enable(self) -> None:
        """
        Enable the functionality and verify actual readback.

        Backend waiting, timeout, and access errors propagate to the caller.
        Invalid or mismatched readback raises :class:`PyAMLException`.
        """
        self._set_enabled(True)

    def disable(self) -> None:
        """
        Disable the functionality and verify actual readback.

        Backend waiting, timeout, and access errors propagate to the caller.
        Invalid or mismatched readback raises :class:`PyAMLException`.
        """
        self._set_enabled(False)

    def is_enabled(self) -> bool:
        """
        Return actual boolean readback, not the commanded state.

        Returns
        -------
        bool
            Whether the functionality is enabled.

        Raises
        ------
        PyAMLException
            If unattached, or if readback is non-boolean or has non-VALID quality.
        """
        return self._binding().readback()

    def _fill_device(self, holder: "ElementHolder") -> None:
        holder._fill_switch_element(self)
