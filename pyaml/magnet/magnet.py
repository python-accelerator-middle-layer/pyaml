"""
Base interfaces for physical and simulated magnets.

This module defines the common magnet element interface and its access to
strength, hardware, and magnet-model information.
"""

import copy
from typing import Self

import numpy as np
from scipy.constants import speed_of_light

from .. import PyAMLException
from ..common import abstract
from ..common.element import Element
from .model import MagnetModel


class Magnet(Element):
    """
    Access one magnet of a physical or simulated lattice.

    A magnet couples a device to its calibration: the attached
    :class:`~pyaml.magnet.model.MagnetModel` owns the strength to hardware-current
    conversion and the underlying control-system device names. The same magnet is
    therefore readable and writable both as a physical strength and as a raw
    hardware value.

    Parameters
    ----------
    name : str
        Element name.
    model : MagnetModel | None, optional
        Magnet model used to convert between strength and hardware value, and to
        resolve the underlying control-system device names.
    lattice_names : str | None, optional
        Name or names of the matching element(s) in the simulated lattice. Defaults
        to ``name``.
    description : str | None, optional
        Human-readable description of the magnet.

    Attributes
    ----------
    strength
        Read/write accessor for the physical strength, in the model's strength unit.
    hardware
        Read/write accessor for the hardware value, in the model's hardware unit.
    model
        Magnet model performing the strength to hardware conversion.

    Methods
    -------
    attach(peer, strength, hardware)
        Return a copy of this magnet bound to one control system or simulator.
    set_energy(energy)
        Set the beam energy, updating the magnetic rigidity used by the model.
    get_model_name()
        Return the name of the attached magnet model.
    set_model_name(name)
        Set the name of the attached magnet model.
    """

    def __init__(
        self, name: str, model: MagnetModel | None = None, lattice_names: str | None = None, description: str | None = None
    ):
        """
        Construct a magnet

        Parameters
        ----------
        name : str
            Element name
        model : MagnetModel
            Magnet model in charge of computing coil(s) current
        """
        super().__init__(name, lattice_names, description)
        self.__model = model
        self.__strength: abstract.ReadWriteFloatScalar = None
        self.__hardware: abstract.ReadWriteFloatScalar = None
        self.__modelName = self.get_name()

    @property
    def strength(self) -> abstract.ReadWriteFloatScalar:
        """
        Gives access to the strength of this magnet in physics unit
        """
        self.check_peer()
        if self.__strength is None:
            raise PyAMLException(f"{str(self)} has no model that supports physics units")
        return self.__strength

    @property
    def hardware(self) -> abstract.ReadWriteFloatScalar:
        """
        Gives access to the strength of this magnet in
        hardware unit when possible
        """
        self.check_peer()
        if self.__hardware is None:
            raise PyAMLException(f"{str(self)} has no model that supports hardware units")
        return self.__hardware

    @property
    def model(self) -> MagnetModel:
        """
        Returns a handle to the underlying magnet model
        """
        return self.__model

    def attach(
        self,
        peer,
        strength: abstract.ReadWriteFloatScalar,
        hardware: abstract.ReadWriteFloatScalar,
    ) -> Self:
        """
        Return a copy of this magnet bound to a control system or simulator.

        Parameters
        ----------
        peer : ElementHolder
            Control system or simulator the copy is bound to.
        strength : abstract.ReadWriteFloatScalar
            Accessor for the physical strength on that peer.
        hardware : abstract.ReadWriteFloatScalar
            Accessor for the hardware value on that peer.

        Returns
        -------
        Self
            Copy of this magnet bound to ``peer``.
        """
        obj = copy.copy(self)
        obj.__modelName = self.__modelName
        obj.__strength = strength
        obj.__hardware = hardware
        obj._peer = peer
        return obj

    def set_energy(self, energy: float):
        """
        Set the energy in eV to compute and set the magnet rigidity
        on the underlying magnet model.
        """
        if self.__model is not None:
            self.__model.set_magnet_rigidity(np.double(energy / speed_of_light))

    def set_model_name(self, name: str):
        """
        Sets the name of this magnet in the model
        (Used for combined function manget)
        """
        self.__modelName = name

    def get_model_name(self) -> str:
        """
        Returns the model name of this magnet
        """
        return self.__modelName

    def __repr__(self):
        """
        Implement the ``__repr__`` string.
        """
        return "%s(peer='%s', name='%s', model_name='%s', magnet_model=%s)" % (
            self.__class__.__name__,
            self.attached_to(),
            self.get_name(),
            self.__modelName,
            repr(self.__model),
        )
