from typing import TYPE_CHECKING

from .. import PyAMLException
from ..common.element import __pyaml_repr__
from ..configuration.factory import ELEMENT_REGISTRY
from ..validation import register_schema
from .function_mapping import function_map
from .linear_serialized_with_trims_model import LinearSerializedMagnetWithTrimsModel
from .magnet import Magnet
from .model import MagnetModel
from .serialized_magnet import SerializedMagnets
from .trim_coil_model import TrimCoilModel

if TYPE_CHECKING:
    from ..common.holders.element_holder import ElementHolder


@register_schema
class SerializedMagnetsWithTrims(SerializedMagnets):
    """A serialized magnet family with independently powered trim coils.

    Main-family behavior is inherited from SerializedMagnets. Each trim defined
    by the serialized model creates a separate magnet with its target member's
    function and lattice element. Each trim model references the serialized
    model's excitation curves. Attached trims are exposed separately from the
    main family members.
    """

    def __init__(
        self,
        name: str,
        function: list[str] | str,
        elements: list[str] | str,
        model: LinearSerializedMagnetWithTrimsModel,
        description: str | None = None,
        peer=None,
    ):
        """Initialize the main family and declare its additional trim magnets."""
        if not isinstance(model, LinearSerializedMagnetWithTrimsModel):
            raise PyAMLException(f"{name}: a LinearSerializedMagnetWithTrimsModel is required")
        if any(trim.name == name for trim in model.trims):
            raise PyAMLException(f"Trim name conflicts with serialized family {name}")
        super().__init__(name, function, elements, model, description, peer)
        self._trim_magnets: list[Magnet] = []
        if peer is None:
            model.set_elements(self.names())
            for trim_index, trim in enumerate(model.trims):
                index = self.names().index(trim.element)
                magnet = function_map[self.functions[index]](
                    name=trim.name,
                    model=TrimCoilModel(model, trim_index),
                    lattice_names=f"list({trim.element})",
                )
                ELEMENT_REGISTRY.register(magnet)
                self._trim_magnets.append(magnet)

    def attach(self, peer, strengths, hardwares, trim_strengths, trim_hardwares) -> list[Magnet]:
        """Attach the main family and its separately exposed trim magnets."""
        attached = super().attach(peer, strengths, hardwares)
        trims = [
            magnet.attach(peer, strength, hardware)
            for magnet, strength, hardware in zip(self._trim_magnets, trim_strengths, trim_hardwares, strict=True)
        ]
        attached[0]._trim_magnets = trims
        return attached + trims

    def get_trim_magnets(self) -> list[Magnet]:
        """Return trim magnets separately from the main family members."""
        return self._trim_magnets

    def _fill_device(self, holder: "ElementHolder") -> None:
        holder._fill_serialized_magnets_with_trims(self)
