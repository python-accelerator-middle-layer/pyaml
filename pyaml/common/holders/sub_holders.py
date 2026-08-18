from typing import TYPE_CHECKING

from ...arrays.bpm_array import BPMArray
from ...arrays.cfm_magnet_array import CombinedFunctionMagnetArray
from ...arrays.magnet_array import MagnetArray
from ...arrays.serialized_magnet_array import SerializedMagnetsArray
from ...bpm.bpm import BPM
from ...magnet.cfm_magnet import CombinedFunctionMagnet
from ...magnet.magnet import Magnet
from ...magnet.serialized_magnet import SerializedMagnets
from .generic_array_holder import GenericArrayHolder
from .generic_element_holder import GenericElementHolder

if TYPE_CHECKING:
    from .element_holder import ElementHolder


class MagnetHolder(GenericElementHolder[Magnet]):
    def __init__(self, peer: "ElementHolder"):
        super().__init__(peer, peer._MAGNETS, "Magnet")


class MagnetsHolder(GenericArrayHolder[Magnet, MagnetArray]):
    def __init__(self, peer: "ElementHolder"):
        super().__init__(
            peer,
            peer._MAGNET_ARRAYS,
            peer.magnet.all,
            peer.magnet.get,
            MagnetArray,
            "Magnet array",
        )


class CombinedFunctionMagnetHolder(GenericElementHolder[CombinedFunctionMagnet]):
    def __init__(self, peer: "ElementHolder"):
        super().__init__(peer, peer._CFM_MAGNETS, "Combined function magnet")


class CombinedFunctionMagnetsHolder(GenericArrayHolder[CombinedFunctionMagnet, CombinedFunctionMagnetArray]):
    def __init__(self, peer: "ElementHolder"):
        super().__init__(
            peer,
            peer._CFM_MAGNET_ARRAYS,
            peer.combined_function_magnet.all,
            peer.combined_function_magnet.get,
            CombinedFunctionMagnetArray,
            "Combined function magnet array",
        )


class SerializedMagnetHolder(GenericElementHolder[SerializedMagnets]):
    def __init__(self, peer: "ElementHolder"):
        super().__init__(peer, peer._SERIALIZED_MAGNETS, "Serialized magnet")


class SerializedMagnetsHolder(GenericArrayHolder[SerializedMagnets, SerializedMagnetsArray]):
    def __init__(self, peer: "ElementHolder"):
        super().__init__(
            peer,
            peer._SERIALIZED_MAGNETS_ARRAYS,
            peer.serialized_magnet.all,
            peer.serialized_magnet.get,
            SerializedMagnetsArray,
            "serialized magnet array",
        )


class BPMHolder(GenericElementHolder[BPM]):
    def __init__(self, peer: "ElementHolder"):
        super().__init__(peer, peer._BPMS, "BPM")


class BPMsHolder(GenericArrayHolder[BPM, BPMArray]):
    def __init__(self, peer: "ElementHolder"):
        super().__init__(
            peer,
            peer._BPM_ARRAYS,
            peer.bpm.all,
            peer.bpm.get,
            BPMArray,
            "BPM array",
        )
