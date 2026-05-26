from scipy.constants import speed_of_light

from ..common import abstract
from ..common.abstract import RWMapper
from ..common.element import Element, ElementSchema, __pyaml_repr__
from ..common.exception import PyAMLException
from ..configuration import Factory
from ..validation import register_schema
from .hcorrector import HCorrector
from .magnet import Magnet, MagnetSchema
from .model import MagnetModel, MagnetModelSchema
from .octupole import Octupole
from .quadrupole import Quadrupole
from .sextupole import Sextupole
from .skewoctu import SkewOctu
from .skewquad import SkewQuad
from .skewsext import SkewSext
from .vcorrector import VCorrector

_fmap: dict = {
    "B0": HCorrector,
    "A0": VCorrector,
    "B1": Quadrupole,
    "A1": SkewQuad,
    "B2": Sextupole,
    "A2": SkewSext,
    "B3": Octupole,
    "A3": SkewOctu,
}


class CombinedFunctionMagnetSchema(ElementSchema):
    mapping: list[list[str]]
    """Name mapping for multipoles
    (i.e. [[B0,C01A-H],[A0,C01A-H],[B2,C01A-S]])"""
    model: MagnetModelSchema | None = None
    """Object in charge of converting magnet strenghts to currents"""


@register_schema(CombinedFunctionMagnetSchema)
class CombinedFunctionMagnet(Element):
    """CombinedFunctionMagnet class"""

    def __init__(self, name: str, mapping: list[list[str]], model: MagnetModel | None = None, peer=None):
        super().__init__(name)
        self._mapping = mapping
        self.model = model
        self.__virtuals: list[Magnet] = []
        self.__strengths: abstract.ReadWriteFloatArray = None
        self.__hardwares: abstract.ReadWriteFloatArray = None

        if peer is None:
            # Configuration part
            if self.model is not None and not hasattr(self.model, "_multipoles"):
                raise PyAMLException(f"{self._name} model: mutipolesfield required for combined function magnet")

            idx = 0
            self.polynoms = []
            for _idx, m in enumerate(self._mapping):
                # Check mapping validity
                if len(m) != 2:
                    raise PyAMLException("Invalid CombinedFunctionMagnet mapping for {m}")
                if m[0] not in _fmap:
                    raise PyAMLException(m[0] + " not implemented for combined function magnet")
                if m[0] not in self.model._multipoles:
                    raise PyAMLException(m[0] + " not found in underlying magnet model")
                self.polynoms.append(_fmap[m[0]].polynom)
                # Create the virtual magnet for the correspoding multipole
                vm = self.__create_virtual_magnet(m[1], m[0])
                self.__virtuals.append(vm)
                # Register the virtual element in the factory to have
                # a coherent factory and improve error reporting
                Factory.register_element(vm)

        else:
            # Attach
            self._peer = peer

    def get_model_name(self) -> str:
        """
        Returns the model name of this magnet
        """
        return self._name

    def __create_vitual_magnet(self, name: str, idx: int) -> Magnet:
        args = {"name": name, "model": self.model}
        mVirtual: Magnet = _fmap[idx](**args)
        mVirtual.set_model_name(self.get_name())
        return mVirtual

    def nb_multipole(self) -> int:
        return len(self._mapping)

    def attach(
        self,
        peer,
        strengths: abstract.ReadWriteFloatArray,
        hardwares: abstract.ReadWriteFloatArray,
    ) -> list[Magnet]:
        l = []
        # Attached the CombinedFunctionMagnet itself
        nCFM = CombinedFunctionMagnet(self._name, self._mapping, self._model, self._peer)
        nCFM.__strengths = strengths
        nCFM.__hardwares = hardwares
        l.append(nCFM)
        # Construct a single function magnet for each multipole
        # of this combined function magnet
        for idx, _m in enumerate(self._mapping):
            strength = RWMapper(strengths, idx)
            hardware = RWMapper(hardwares, idx) if self.model.has_hardware() else None
            l.append(self.__virtuals[idx].attach(peer, strength, hardware))
        return l

    @property
    def strengths(self) -> abstract.ReadWriteFloatScalar:
        """
        Gives access to the strengths of this combined
        function magnet in physics unit
        """
        self.check_peer()
        if self.__strengths is None:
            raise PyAMLException(f"{str(self)} has no model that supports physics units")
        return self.__strengths

    @property
    def hardwares(self) -> abstract.ReadWriteFloatScalar:
        """
        Gives access to the strengths of this combined
        function magnet in hardware unit when possible
        """
        self.check_peer()
        if self.__hardwares is None:
            raise PyAMLException(f"{str(self)} has no model that supports hardware units")
        return self.__hardwares

    def set_energy(self, E: float):
        if self.model is not None:
            self.model.set_magnet_rigidity(E / speed_of_light)

    def __repr__(self):
        return __pyaml_repr__(self)
