"""Serialized magnet excitation model with independently powered trim coils."""

from ..common.exception import PyAMLException
from ..validation import register_schema
from .curve import Curve
from .linear_serialized_model import LinearSerializedMagnetModel
from .trim_coil import TrimCoil

PYAMLCLASS = "LinearSerializedMagnetWithTrimsModel"


@register_schema
class LinearSerializedMagnetWithTrimsModel(LinearSerializedMagnetModel):
    """
    Extend a serialized magnet model with incremental trim strengths.

    The inherited conversions and device names describe the main series only.
    Trim conversions take the main current explicitly and use the calibrated
    submodel of the addressed member. For its excitation function ``f``,
    ``trim_strength = f(main_current + trim_factor * trim_current) - f(main_current)``.
    Trim currents are physical supply currents; the signed factor converts them
    to equivalent main-coil currents. Inversion uses the submodel's existing
    interpolation and clipping conventions.

    Parameters
    ----------
    curves : Curve or list[Curve]
        Main excitation curves, as in :class:`LinearSerializedMagnetModel`.
    trims : list[TrimCoil]
        Trim definitions containing ``element``, ``name``, ``powerconverter``,
        and optionally ``trim_factor`` (default 1) and ``hardware_unit``
        (defaulting to the main hardware unit). List order defines trim indices.
    calibration_factors, calibration_offsets, crosstalk, polarities, powerconverter, unit, hardware_unit
        Main-series parameters, passed to :class:`LinearSerializedMagnetModel`.

    Notes
    -----
    Call ``set_elements(elements)`` to resolve trim targets and initialize the
    main submodels, then set the magnetic rigidity before converting strengths.
    Members without a trim definition remain ordinary series members.

    Configuration
    -------------
    .. code-block:: yaml

        type: pyaml.magnet.linear_serialized_with_trims_model
        unit: rad
        hardware_unit: A
        curves:
          type: pyaml.magnet.csvcurve
          file: sr/magnet_models/serialized_strength.csv
        powerconverter: mag/mySeries/current
        trims:
          - class: pyaml.magnet.trim_coil.TrimCoil
            element: D1
            name: TRIM_D1
            trim_factor: 1.0
            hardware_unit: A
            powerconverter: mag/D1/trim_current
    """

    def __init__(
        self,
        curves: Curve | list[Curve],
        trims: list[TrimCoil],
        calibration_factors: float | list[float] | None = None,
        calibration_offsets: float | list[float] | None = None,
        polarities: int | list[int] | None = None,
        powerconverter: str | None = None,
        unit: str | None = None,
        hardware_unit: str | None = None,
    ):
        """Initialize the main series and its trim definitions."""
        super().__init__(
            curves=curves,
            calibration_factors=calibration_factors,
            calibration_offsets=calibration_offsets,
            polarities=polarities,
            powerconverter=powerconverter,
            unit=unit,
            hardware_unit=hardware_unit,
        )
        self.trims = list(trims)
        self._trim_indices: list[int] | None = None
        for key in ("element", "name"):
            if len({getattr(trim, key) for trim in self.trims}) != len(self.trims):
                raise PyAMLException(f"Trim {key} values must be unique")

    def set_elements(self, elements: list[str]):
        """Initialize main submodels and resolve trim targets against member names."""
        indices = []
        for trim in self.trims:
            if elements.count(trim.element) != 1:
                raise PyAMLException(f"Trim target {trim.element} must identify exactly one series member")
            if trim.name in elements:
                raise PyAMLException(f"Trim name {trim.name} conflicts with a series member")
            indices.append(elements.index(trim.element))
        self.set_number_of_magnets(len(elements))
        self._trim_indices = indices

    def set_number_of_magnets(self, nb_magnets: int):
        """Rebuild main submodels and invalidate any previous trim mapping."""
        super().set_number_of_magnets(nb_magnets)
        self._trim_indices = None

    def _trim_sub_model(self, trim_index: int):
        """Return the main excitation model addressed by a trim."""
        if self._trim_indices is None:
            raise PyAMLException("Call set_elements before converting trim strengths")
        if not 0 <= trim_index < len(self.trims):
            raise IndexError(trim_index)
        return self.get_sub_model(self._trim_indices[trim_index])

    def compute_trim_strength(self, trim_index: int, main_current: float, trim_current: float) -> float:
        """Return the incremental trim strength at the supplied main current."""
        model = self._trim_sub_model(trim_index)
        total_current = main_current + self.trims[trim_index].trim_factor * trim_current
        return float(model.compute_strengths([total_current])[0] - model.compute_strengths([main_current])[0])

    def compute_trim_current(self, trim_index: int, main_current: float, trim_strength: float) -> float:
        """Return the physical trim current giving an incremental strength."""
        model = self._trim_sub_model(trim_index)
        main_strength = model.compute_strengths([main_current])[0]
        total_current = model.compute_hardware_values([main_strength + trim_strength])[0]
        return float((total_current - main_current) / self.trims[trim_index].trim_factor)

    def get_trim_device_names(self) -> list[str]:
        """Return trim supply names in trim configuration order."""
        return [trim.powerconverter for trim in self.trims]

    def get_trim_hardware_units(self) -> list[str | None]:
        """Return trim current units in trim configuration order."""
        return [trim.hardware_unit if trim.hardware_unit is not None else self._hardware_unit for trim in self.trims]
