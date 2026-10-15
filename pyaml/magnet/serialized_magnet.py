"""
Serialized magnet elements.

This module defines magnet elements composed of multiple serialized magnets.
"""

from typing import TYPE_CHECKING

import numpy as np
from scipy.constants import speed_of_light

from .. import PyAMLException
from ..common import abstract
from ..common.element import Element, __pyaml_repr__
from ..configuration.factory import ELEMENT_REGISTRY
from ..validation import DynamicValidation, register_schema
from .function_mapping import function_map
from .magnet import Magnet
from .model import MagnetModel

if TYPE_CHECKING:
    from ..common.holders.element_holder import ElementHolder

# Define the main class name for this module
PYAMLCLASS = "SerializedMagnets"


class ReadWriteSerializedHardware(abstract.ReadWriteFloatScalar):
    """
    Read/write access to the hardware value of a serialized-magnet family.

    The family has a single degree of freedom, the hardware value ``I`` of its
    power supply, shared by every magnet of the series.

    Parameters
    ----------
    hardwares : list[abstract.ReadWriteFloatScalar]
        Per-magnet hardware accessors. Writing one of them moves the whole series.
    model : MagnetModel
        Serialized magnet model used for units and rigidity.

    Methods
    -------
    get()
        Return the shared hardware value ``I``.
    set(value)
        Set the shared hardware value ``I``.
    set_and_wait(value)
        Set the shared hardware value and wait for convergence.
    unit()
        Return the hardware-value unit.
    get_model()
        Return the magnet conversion model.
    set_magnet_rigidity(brho)
        Set the magnetic rigidity used for conversion.
    """

    def __init__(self, hardwares: list[abstract.ReadWriteFloatScalar], model: MagnetModel):
        """
        Initialize a family hardware accessor for serialized magnets.
        """
        self._hardwares = hardwares
        self._model = model

    def get(self) -> float:
        """Return the shared hardware value ``I``."""
        return self._hardwares[0].get()

    def set(self, value: float):
        """
        Set the shared hardware value ``I``.

        Parameters
        ----------
        value : float
            Hardware value applied to the power supply of the series.
        """
        self._hardwares[0].set(value)

    def set_and_wait(self, value: float):
        """
        Set the shared hardware value and wait for convergence.

        Parameters
        ----------
        value : float
            Hardware value applied to the power supply of the series.

        Raises
        ------
        NotImplementedError
            Waiting for readback convergence is not implemented for this accessor.
        """
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        """Return the hardware-value unit."""
        return self._model.get_hardware_units()[0]

    def get_model(self) -> MagnetModel:
        """Return the magnet conversion model."""
        return self._model

    def set_magnet_rigidity(self, brho: np.double):
        """
        Set the magnetic rigidity used for conversion.

        Parameters
        ----------
        brho : np.double
            Magnetic rigidity in tesla metres, forwarded to the magnet model.
        """
        self._model.set_magnet_rigidity(brho)


class ReadWriteSerializedStrength(ReadWriteSerializedHardware):
    """
    Read/write access to the average strength of a serialized-magnet family.

    Magnet ``i`` of the series has the strength ``k_i = f_i(I)``. The family
    strength is the average strength ``sum(f_i(I)) / N``.

    Parameters
    ----------
    hardwares : list[abstract.ReadWriteFloatScalar]
        Per-magnet hardware accessors. Writing one of them moves the whole series.
    model : MagnetModel
        Serialized magnet model converting between average strength and hardware value.

    Methods
    -------
    get()
        Return the average strength of the series.
    set(value)
        Set the hardware value giving the requested average strength.
    unit()
        Return the physical strength unit.
    """

    def get(self) -> float:
        """Return the average strength of the series."""
        return self._model.compute_mean_strength(self._hardwares[0].get())

    def set(self, value: float):
        """
        Set the hardware value giving the requested average strength.

        Parameters
        ----------
        value : float
            Average strength of the series.
        """
        self._hardwares[0].set(self._model.compute_hardware_from_mean_strength(value))

    def unit(self) -> str:
        """Return the physical strength unit."""
        return self._model.get_strength_units()[0]


@register_schema
class SerializedMagnets(Element, DynamicValidation):
    """
    Serialized group of magnets that share the same set point.

    This class represents a set of magnets that are controlled together as a
    single logical device. The serialized magnets may be driven by one power
    supply or by several power supplies, but they share a common physics or
    hardware set point through a combined read/write interface.

    Parameters
    ----------
    name : str
        Name of the serialized magnet group.
    function : str
        Magnet function identifier used to select the concrete virtual magnet type.
    elements : list[str] | str
        Names of the individual magnets in the group.
    model : MagnetModel | None, optional
        Magnet model used to convert between strengths and hardware values.
    description : str | None, optional
        Human-readable description of the serialized magnet group.
    peer : object, optional
        Control-system or simulator peer used when attaching the magnet group.

    Attributes
    ----------
    strength
        Average strength of the magnets of the series, in physics unit
    hardware
        Hardware value of the power supply shared by the series

    Methods
    -------
    get_nb_magnets()
        Return the number of magnets in the serialized group.
    get_magnets()
        Return the group's virtual single-function magnets.
    attach(peer, strengths, hardwares)
        Attach the group and its virtual magnets to a runtime peer.
    set_energy(energy)
        Set beam energy for serialized-magnet strength conversion.
    get_device_names()
        Return the associated device names.

    Raises
    ------
    PyAMLException
        If the requested function is not implemented or if the configuration is
        invalid.

    Notes
    -----
    The serialized group stores a virtual magnet for each underlying element. When
    attached, each virtual magnet is bound to the same peer and the group exposes
    family strength and hardware accessors.

    The series has a single degree of freedom, the power-supply hardware value ``I``.
    Magnet ``i`` has the strength ``k_i = f_i(I)``:

    ====================== =============================== ==================================================
    Accessor               ``get()``                       ``set(x)``
    ====================== =============================== ==================================================
    ``family.hardware``    ``I``                           write ``I = x``
    ``family.strength``    average ``sum(f_i(I)) / N``     solve ``sum(f_i(I)) / N = x`` for ``I``, write it
    ``magnet[i].hardware`` ``I``                           write ``I = x``, all the magnets follow
    ``magnet[i].strength`` ``k_i = f_i(I)``                write ``I = f_i^-1(x)``, the others follow
    ====================== =============================== ==================================================

    Configuration
    -------------
    The model can be defined inline or in a separate file. See
    :mod:`pyaml.magnet.model` and its subclasses for model configuration.

    .. code-block:: yaml

        - type: pyaml.magnet.serialized_magnet
          name: SERIALIZED_QUADRUPOLES
          function: B1
          elements:
            - QUADRUPOLE_1
            - QUADRUPOLE_2
          model: path/to/serialized_magnet_model.yaml
    """

    def __init__(
        self,
        name: str,
        function: str,
        elements: list[str] | str,
        model: MagnetModel | None = None,
        description: str | None = None,
        peer=None,
    ):
        """
        Initialize a group of magnets sharing one setpoint.
        """
        super().__init__(name, None, description)

        self.function = function
        self.model = model

        self.polynom = None
        self.__strengths = None
        self.__hardwares = None
        self.__virtuals: list[Magnet] = []
        self.__elements = elements if isinstance(elements, list) else [elements]
        if peer is None:
            # Configuration part
            # The submodels are built once here: the attached copies share them with the per-magnet accessors
            self.model.set_number_of_magnets(len(self.__elements))
            self.polynom = function_map[self.function].polynom
            if self.function not in function_map:
                raise PyAMLException(self.function + " not implemented for serialized magnet")
            for element in self.__elements:
                # Check mapping validity
                # Create the virtual magnet for the corresponding magnet
                vm = self.__create_virtual_magnet(element)
                self.__virtuals.append(vm)
                # Register the virtual element in the factory to have a coherent factory and improve error reporting
                ELEMENT_REGISTRY.register(vm)
        else:
            # Attach
            self._peer = peer

    def _fill_device(self, holder: "ElementHolder") -> None:
        holder._fill_serialized_magnets(self)

    def __create_virtual_magnet(self, name: str) -> Magnet:
        """
        Create a virtual magnet for one serialized element.

        The configured function mapping selects the concrete magnet class, and
        the serialized group's model is shared with the new virtual magnet.

        Parameters
        ----------
        name : str
            Name assigned to the virtual magnet.

        Returns
        -------
        Magnet
            Newly created virtual magnet linked to the serialized group.
        """
        args = {"name": name, "model": self.model}
        virtual: Magnet = function_map[self.function](**args)
        virtual.set_model_name(self.get_name())
        return virtual

    def get_nb_magnets(self) -> int:
        """Return the number of magnets in the serialized group."""
        return len(self.__elements)

    def get_magnets(self) -> list[Magnet]:
        """Return the group's virtual single-function magnets."""
        return self.__virtuals

    def attach(
        self,
        peer,
        strengths: list[abstract.ReadWriteFloatScalar],
        hardwares: list[abstract.ReadWriteFloatScalar],
    ) -> list[Magnet]:
        """
        Attach the group and its virtual magnets to a runtime peer.

        Parameters
        ----------
        peer : object
            Control system or simulator the group is bound to.
        strengths : list[abstract.ReadWriteFloatScalar]
            Strength accessor of each magnet in the group, in declaration order.
        hardwares : list[abstract.ReadWriteFloatScalar]
            Hardware accessor of each magnet in the group, in declaration order.

        Returns
        -------
        list[Magnet]
            Virtual magnets of the group, each bound to ``peer``.
        """
        l = []
        n_ser_mag = SerializedMagnets(self._name, self.function, self.__elements, self.model, self.description, peer)
        if self.model.has_hardware():
            n_ser_mag.__hardwares = ReadWriteSerializedHardware(hardwares, self.model)
            if self.model.has_physics():
                n_ser_mag.__strengths = ReadWriteSerializedStrength(hardwares, self.model)
        l.append(n_ser_mag)
        # Construct a single magnet for each magnet.
        sub_magnets: list[Magnet] = []
        for idx, _ in enumerate(self.__elements):
            strength = strengths[idx]
            hardware = hardwares[idx] if self.model.has_hardware() else None
            sub_magnets.append(self.__virtuals[idx].attach(peer, strength, hardware))
        n_ser_mag.__virtuals.extend(sub_magnets)
        l.extend(sub_magnets)
        return l

    @property
    def strength(self) -> abstract.ReadWriteFloatScalar:
        """
        Average strength of the magnets of the series, in physics unit
        """
        self.check_peer()
        if self.__strengths is None:
            raise PyAMLException(f"{str(self)} has no model that supports physics units")
        return self.__strengths

    @property
    def hardware(self) -> abstract.ReadWriteFloatScalar:
        """
        Hardware value of the power supply shared by the series
        """
        self.check_peer()
        if self.__hardwares is None:
            raise PyAMLException(f"{str(self)} has no model that supports hardware units")
        return self.__hardwares

    def set_energy(self, energy: float):
        """
        Set beam energy for serialized-magnet strength conversion.

        The energy is converted to magnetic rigidity and propagated to the
        serialized magnet model.

        Parameters
        ----------
        energy : float
            Beam energy in electronvolts.
        """
        brho = energy / speed_of_light
        if self.model is not None:
            self.model.set_magnet_rigidity(brho)
        if self.__hardwares is not None:
            self.__hardwares.set_magnet_rigidity(brho)
        if self.__strengths is not None:
            self.__strengths.set_magnet_rigidity(brho)

    def __repr__(self):
        """
        Implement the ``__repr__`` string.
        """
        return __pyaml_repr__(self)

    def get_device_names(self) -> list[str | None]:
        """Return the associated device names."""
        return self.model.get_device_names()
