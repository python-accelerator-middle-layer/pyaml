"""Trim-coil conversion and metadata backed by the serialized magnet model."""

import numpy as np

from ..common.exception import PyAMLException
from .linear_serialized_with_trims_model import LinearSerializedMagnetWithTrimsModel
from .model import MagnetModel


class TrimCoilModel(MagnetModel):
    """Describe one trim supply without defining independent excitation curves.

    Instances are created by SerializedMagnetsWithTrims. The trim index follows
    the serialized model's trim configuration order, not its main-member order.
    Conversions require an explicit main current. The model performs no device
    reads and retains no current values between calls.
    """

    def __init__(self, serialized_model: LinearSerializedMagnetWithTrimsModel, trim_index: int):
        self.serialized_model = serialized_model
        self.trim_index = trim_index

    def get_device_names(self) -> list[str]:
        """Return the trim's independent power-converter reference."""
        return [self.serialized_model.get_trim_device_names()[self.trim_index]]

    def get_strength_units(self) -> list[str]:
        """Use the strength unit of the main member carrying this trim."""
        return self.serialized_model._trim_sub_model(self.trim_index).get_strength_units()

    def get_hardware_units(self) -> list[str | None]:
        """Use the configured trim unit, or inherit the main hardware unit."""
        return [self.serialized_model.get_trim_hardware_units()[self.trim_index]]

    def set_magnet_rigidity(self, brho):
        """Forward rigidity to the model owning the excitation curves."""
        self.serialized_model.set_magnet_rigidity(brho)

    def compute_strengths(self, hardware_values, main_current: float | None = None) -> np.ndarray:
        """Return the incremental strength for one trim current at the main current.

        Calibration, signed trim factors and clipping follow the serialized
        model's conversion. The result is a one-element array.
        """
        if main_current is None:
            raise PyAMLException("Trim strength conversion requires the main current")
        return np.array([self.serialized_model.compute_trim_strength(self.trim_index, main_current, hardware_values[0])])

    def compute_hardware_values(self, strengths, main_current: float | None = None) -> np.ndarray:
        """Return one trim current for an incremental strength at the main current.

        Inversion and clipping follow the serialized model's conversion.
        """
        if main_current is None:
            raise PyAMLException("Trim current conversion requires the main current")
        return np.array([self.serialized_model.compute_trim_current(self.trim_index, main_current, strengths[0])])
