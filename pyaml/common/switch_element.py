"""Switchable accelerator functionality without a required lattice counterpart."""

import copy
from typing import TYPE_CHECKING, Self

from ..validation import DynamicValidation, register_schema
from . import abstract
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

    Attributes
    ----------
    enabled
        Boolean get/set accessor, shared by control-system and simulator modes.

    Notes
    -----
    Control-system access uses the reusable RWScalarBoolean adapter: get()
    reads the backend readback (including numeric 0/1 flags) and set() writes
    a Python boolean through DeviceAccess.set(). Value metadata is unwrapped;
    this interface adds no quality, waiting, or completion policy. Backend
    errors propagate. Construction and attachment never initialize hardware.

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
        enabled = feedback.enabled.get()
        feedback.enabled.set(True)
        feedback.enable()

        simulated_feedback = sr.design["SOFB"]
        assert simulated_feedback.enabled.get() is False
        simulated_feedback.enabled.set(True)  # Does not affect hardware or the lattice.
    """

    __pyaml_repr_exclude__ = ("enabled",)

    def __init__(self, name: str, device: str, description: str | None = None):
        """Initialize the element configuration without accessing hardware."""
        super().__init__(name=name, description=description)
        self.device = device
        self._enabled: abstract.RWScalarBoolean | None = None

    def attach(self, peer: "ElementHolder", enabled: abstract.RWScalarBoolean) -> Self:
        """
        Return a copy bound to a peer and its boolean state interface.

        Parameters
        ----------
        peer : ElementHolder
            Control system or simulator owning this runtime element.
        enabled : abstract.RWScalarBoolean
            Boolean get/set interface owned by this attachment.

        Returns
        -------
        Self
            Attached copy; the original configuration remains unattached.
        """
        obj = copy.copy(self)
        obj._enabled = enabled
        obj._peer = peer
        return obj

    @property
    def enabled(self) -> abstract.RWScalarBoolean:
        """Return the boolean get/set accessor for this holder."""
        if self._enabled is None:
            raise PyAMLException(f"{self.name}: enabled state is unavailable before attachment")
        return self._enabled

    def enable(self) -> None:
        """Enable the functionality through its boolean accessor."""
        self.enabled.set(True)

    def disable(self) -> None:
        """Disable the functionality through its boolean accessor."""
        self.enabled.set(False)

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
            If unattached, or if the backend value is not a boolean flag.
        """
        return self.enabled.get()

    def _fill_device(self, holder: "ElementHolder") -> None:
        holder._fill_switch_element(self)
