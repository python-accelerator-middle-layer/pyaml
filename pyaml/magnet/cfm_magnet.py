"""
Combined-function magnet elements.

This module defines magnets that combine multiple multipole components and
provide separate strength and hardware access for those components.
"""

from scipy.constants import speed_of_light

from ..common import abstract
from ..common.abstract import RWMapper
from ..common.element import Element, __pyaml_repr__
from ..common.exception import PyAMLException
from ..configuration.factory import ELEMENT_REGISTRY
from ..validation import DynamicValidation, register_schema
from .hcorrector import HCorrector
from .magnet import Magnet
from .model import MagnetModel
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

# Define the main class name for this module
PYAMLCLASS = "CombinedFunctionMagnet"


@register_schema
class CombinedFunctionMagnet(Element, DynamicValidation):
    """
    Combined function magnet made up of several virtual single-function magnets.

    This class represents a magnet whose effect is described by multiple multipole
    components, such as a corrector, quadrupole, sextupole, or octupole family.
    Each entry in ``mapping`` creates a virtual magnet backed by the same
    underlying magnet model, and the virtual magnets are exposed as individual
    elements while still belonging to the same combined-function object.

    Parameters
    ----------
    name : str
        Name of the combined-function magnet.
    mapping : list[list[str]]
        List of ``[multipole, magnet_name]`` pairs. The first entry selects the
        virtual magnet type, and the second entry gives the name of the virtual
        magnet.
    model : MagnetModel | None, optional
        Magnet model used to convert strengths to hardware values and vice versa.
    description : str | None, optional
        Human-readable description of the magnet.
    peer : object, optional
        Control-system or simulator peer used when attaching the magnet.

    Raises
    ------
    PyAMLException
        If the mapping is invalid, if an unsupported multipole is requested, or
        if the model does not provide the required multipole information.
    """

    def __init__(
        self, name: str, mapping: list[list[str]], model: MagnetModel | None = None, description: str | None = None, peer=None
    ):
        """
        Initialize the CombinedFunctionMagnet.

        Parameters
        ----------
        name : str
            Name of the combined-function magnet.
        mapping : list[list[str]]
            List of ``[multipole, magnet_name]`` pairs. The first entry selects the virtual magnet type, and the second
            entry gives the name of the virtual magnet.
        model : MagnetModel | None
            Magnet model used to convert strengths to hardware values and vice versa.
        description : str | None
            Human-readable description of the magnet.
        peer : object
            Control-system or simulator peer used when attaching the magnet.
        """
        super().__init__(name, None, description)

        self._mapping = mapping
        self.model = model
        self.__virtuals: list[Magnet] = []
        self.__strengths: abstract.ReadWriteFloatArray | None = None
        self.__hardwares: abstract.ReadWriteFloatArray | None = None

        if peer is None:
            # Configuration part
            if self.model is not None and not hasattr(self.model, "multipoles"):
                raise PyAMLException(f"{name} model: mutipoles field required for combined function magnet")

            idx = 0
            self.polynoms = []
            for _idx, m in enumerate(self._mapping):
                # Check mapping validity
                if len(m) != 2:
                    raise PyAMLException("Invalid CombinedFunctionMagnet mapping for {m}")
                if m[0] not in _fmap:
                    raise PyAMLException(m[0] + " not implemented for combined function magnet")
                if m[0] not in self.model.multipoles:
                    raise PyAMLException(m[0] + " not found in underlying magnet model")
                self.polynoms.append(_fmap[m[0]].polynom)
                # Create the virtual magnet for the correspoding multipole
                vm = self.__create_virutal_manget(m[1], m[0])
                self.__virtuals.append(vm)
                # Register the virtual element in the factory to have
                # a coherent factory and improve error reporting
                ELEMENT_REGISTRY.register(vm)

        else:
            # Attach
            self._peer = peer

    def get_model_name(self) -> str:
        """
        Returns the model name of this magnet
        """
        return self._name

    def __create_virutal_manget(self, name: str, idx: int) -> Magnet:
        """
        Create a virtual magnet for one multipole component.

        The virtual magnet provides the standard single-function magnet
        interface for a component of this combined-function magnet.

        Parameters
        ----------
        name : str
            Name assigned to the virtual magnet.
        idx : int
            Multipole key used to select the virtual-magnet class.

        Returns
        -------
        Magnet
            Newly created virtual magnet linked to this magnet's model.
        """
        args = {"name": name, "model": self.model}
        mVirtual: Magnet = _fmap[idx](**args)
        mVirtual.set_model_name(self.get_name())
        return mVirtual

    def nb_multipole(self) -> int:
        """Return the number of configured multipole components."""
        return len(self._mapping)

    def attach(
        self,
        peer,
        strengths: abstract.ReadWriteFloatArray,
        hardwares: abstract.ReadWriteFloatArray,
    ) -> list[Magnet]:
        """
        Attach the combined-function magnet and its virtual components.

        The returned list contains the attached combined-function magnet
        followed by one attached single-function virtual magnet per configured
        multipole. Each virtual magnet receives a mapped view of the shared
        strength and hardware arrays.

        Parameters
        ----------
        peer : object
            Simulator or control-system element holder.
        strengths : abstract.ReadWriteFloatArray
            Array accessor for the physical multipole strengths.
        hardwares : abstract.ReadWriteFloatArray
            Array accessor for the hardware values.

        Returns
        -------
        list[Magnet]
            Attached combined-function magnet and its virtual component
            magnets.
        """
        l = []
        # Attached the CombinedFunctionMagnet itself
        nCFM = CombinedFunctionMagnet(self._name, self._mapping, self.model, self._description, peer)
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
        """
        Set beam energy for magnetic-strength conversion.

        The energy is converted from electronvolts to magnetic rigidity and
        supplied to the underlying combined-function magnet model.

        Parameters
        ----------
        E : float
            Beam energy in electronvolts.
        """
        if self.model is not None:
            self.model.set_magnet_rigidity(E / speed_of_light)

    def __repr__(self):
        """
        Implement the ``__repr__`` string.
        """
        return __pyaml_repr__(self)
