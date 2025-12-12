import numpy as np
from numpy import double
from numpy.typing import NDArray

from ..bpm.bpm_model import BPMModel
from ..common import abstract
from ..common.abstract_aggregator import ScalarAggregator
from ..control.deviceaccess import DeviceAccess
from ..control.deviceaccesslist import DeviceAccessList
from ..magnet.magnet import Magnet
from ..magnet.model import MagnetModel
from ..rf.rf_plant import RFPlant
from ..rf.rf_transmitter import RFTransmitter

# ------------------------------------------------------------------------------


class CSScalarAggregator(ScalarAggregator):
    """
    Basic control system aggregator for a list of scalar values
    """

    def __init__(self, devs: DeviceAccessList):
        self._devs = devs

    def add_devices(self, devices: DeviceAccess | list[DeviceAccess]):
        self._devs.add_devices(devices)

    def set(self, value: NDArray[np.float64]):
        self._devs.set(value)

    def set_and_wait(self, value: NDArray[np.float64]):
        self._devs.set_and_wait(value)

    def get(self) -> NDArray[np.float64]:
        return self._devs.get()

    def readback(self) -> np.array:
        return self._devs.readback()

    def unit(self) -> str:
        return self._devs.unit()

    def nb_device(self) -> int:
        return self._devs.__len__()


# ------------------------------------------------------------------------------


class CSStrengthScalarAggregator(CSScalarAggregator):
    """
    Control system aggregator for a list of magnet strengths.
    This aggregator is in charge of computing hardware setpoints
    and applying them without overlap.
    When virtual magnets exported from combined function mangets are present (RWMapper),
    the aggregator prevents to apply several times the same power supply setpoint.
    """

    def __init__(self, peer: CSScalarAggregator):
        CSScalarAggregator.__init__(self, peer._devs)
        self.__models: list[MagnetModel] = []  # List of magnet model
        self.__modelToMagnet: list[list[tuple[int, int]]] = []  # strengths indexing
        self.__nbMagnet = 0  # Number of magnet strengths

    def add_magnet(self, magnet: Magnet, devs: list[DeviceAccess]):
        # Incoming magnet can be a magnet exported from
        # a CombinedFunctionMagnet or simple magnet.
        # All magnets exported from a same CombinedFunctionMagnet share the same model
        # TODO: check that strength is supported (m.strength may be None)
        strengthIndex = (
            magnet.strength.index()
            if isinstance(magnet.strength, abstract.RWMapper)
            else 0
        )
        if magnet.model not in self.__models:
            index = len(self.__models)
            self.__models.append(magnet.model)
            self.__modelToMagnet.append([(self.__nbMagnet, strengthIndex)])
            self._devs.add_devices(devs)
        else:
            index = self.__models.index(magnet.model)
            self.__modelToMagnet[index].append((self.__nbMagnet, strengthIndex))
        self.__nbMagnet += 1

    def set(self, value: NDArray[np.float64]):
        allHardwareValues = self._devs.get()  # Read all hardware setpoints
        newHardwareValues = np.zeros(self.nb_device())
        hardwareIndex = 0
        for modelIndex, model in enumerate(self.__models):
            nbDev = len(model.get_devices())
            mStrengths = model.compute_strengths(
                allHardwareValues[hardwareIndex : hardwareIndex + nbDev]
            )
            for valueIdx, strengthIdx in self.__modelToMagnet[modelIndex]:
                mStrengths[strengthIdx] = value[valueIdx]
            newHardwareValues[hardwareIndex : hardwareIndex + nbDev] = (
                model.compute_hardware_values(mStrengths)
            )
            hardwareIndex += nbDev
        self._devs.set(newHardwareValues)

    def set_and_wait(self, value: NDArray[np.float64]):
        raise NotImplementedError("Not implemented yet.")

    def get(self) -> NDArray[np.float64]:
        allHardwareValues = self._devs.get()  # Read all hardware setpoints
        allStrength = np.zeros(self.__nbMagnet)
        hardwareIndex = 0
        for modelIndex, model in enumerate(self.__models):
            nbDev = len(model.get_devices())
            mStrengths = model.compute_strengths(
                allHardwareValues[hardwareIndex : hardwareIndex + nbDev]
            )
            for valueIdx, strengthIdx in self.__modelToMagnet[modelIndex]:
                allStrength[valueIdx] = mStrengths[strengthIdx]
            hardwareIndex += nbDev
        return allStrength

    def readback(self) -> np.array:
        allHardwareValues = self._devs.readback()  # Read all hardware readback
        allStrength = np.zeros(self.__nbMagnet)
        hardwareIndex = 0
        for modelIndex, model in enumerate(self.__models):
            nbDev = len(model.get_devices())
            mStrengths = model.compute_strengths(
                allHardwareValues[hardwareIndex : hardwareIndex + nbDev]
            )
            for valueIdx, strengthIdx in self.__modelToMagnet[modelIndex]:
                allStrength[valueIdx] = mStrengths[strengthIdx]
            hardwareIndex += nbDev
        return allStrength

    def unit(self) -> str:
        return self._devs.unit()


# ------------------------------------------------------------------------------


class RWHardwareScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a magnet
    of a control system (in hardware units)
    """

    def __init__(self, model: MagnetModel, dev: DeviceAccess):
        self.__model = model
        self.__dev = dev

    def get(self) -> float:
        return self.__dev.get()

    def set(self, value: float):
        self.__dev.set(value)

    def set_and_wait(self, value: double):
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        return self.__model.get_hardware_units()[0]


# ------------------------------------------------------------------------------


class RWStrengthScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a strength of a control system
    """

    def __init__(self, model: MagnetModel, dev: DeviceAccess):
        self.__model = model
        self.__dev = dev

    # Gets the value
    def get(self) -> float:
        current = self.__dev.get()
        return self.__model.compute_strengths([current])[0]

    # Sets the value
    def set(self, value: float):
        current = self.__model.compute_hardware_values([value])[0]
        self.__dev.set(current)

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value: float):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> str:
        return self.__model.get_strength_units()[0]


# ------------------------------------------------------------------------------


class RWHardwareArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to a magnet array
    of a control system (in hardware units)
    """

    def __init__(self, model: MagnetModel, devs: list[DeviceAccess]):
        self.__model = model
        self.__devs = devs

    # Gets the value
    def get(self) -> np.array:
        return np.array([p.get() for p in self.__devs])

    # Sets the value
    def set(self, value: np.array):
        for idx, p in enumerate(self.__devs):
            p.set(value[idx])

    # Sets the value and waits that the read value reach the setpoint
    def set_and_wait(self, value: np.array):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> list[str]:
        return self.__model.get_hardware_units()


# ------------------------------------------------------------------------------


class RWStrengthArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to magnet strengths of a control system
    """

    def __init__(self, model: MagnetModel, devs: list[DeviceAccess]):
        self.__model = model
        self.__devs = devs

    # Gets the value
    def get(self) -> np.array:
        r = np.array([p.get() for p in self.__devs])
        str = self.__model.compute_strengths(r)
        return str

    # Sets the value
    def set(self, value: np.array):
        cur = self.__model.compute_hardware_values(value)
        for idx, p in enumerate(self.__devs):
            p.set(cur[idx])

    # Sets the value and waits that the read value reach the setpoint
    def set_and_wait(self, value: np.array):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> list[str]:
        return self.__model.get_strength_units()


# ------------------------------------------------------------------------------


class RBpmArray(abstract.ReadFloatArray):
    """
    Class providing read access to a BPM array of a control system
    """

    def __init__(self, model: BPMModel, devs: list[DeviceAccess]):
        self.__model = model
        self.__devs = devs

    # Gets the values
    def get(self) -> np.array:
        return np.array([self.__devs[0].get(), self.__devs[1].get()])

    # Gets the unit of the value Assume that x and y has the same unit
    def unit(self) -> str:
        return self.__model.get_pos_devices()[0].unit()


# ------------------------------------------------------------------------------


class RWBpmTiltScalar(abstract.ReadFloatScalar):
    """
    Class providing read access to a BPM tilt of a control system
    """

    def __init__(self, model: BPMModel, dev: DeviceAccess):
        self.__model = model
        self.__dev = dev

    # Gets the value
    def get(self) -> float:
        return self.__dev.get()

    def set(self, value: float):
        self.__dev.set(value)

    def set_and_wait(self, value: NDArray[np.float64]):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> str:
        return self.__model.get_tilt_device().unit()


# ------------------------------------------------------------------------------


class RWBpmOffsetArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to a BPM offset of a control system
    """

    def __init__(self, model: BPMModel, devs: list[DeviceAccess]):
        self.__model = model
        self.__devs = devs

    # Gets the value
    def get(self) -> NDArray[np.float64]:
        return np.array([self.__devs[0].get(), self.__devs[1].get()])

    # Sets the value
    def set(self, value: NDArray[np.float64]):
        self.__devs[0].set(value[0])
        self.__devs[1].set(value[1])

    def set_and_wait(self, value: NDArray[np.float64]):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> str:
        return self.__model.get_offset_devices()[0].unit()


# ------------------------------------------------------------------------------


class RWRFVoltageScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to cavity voltage
    for a transmitter of a control system.
    """

    def __init__(self, transmitter: RFTransmitter, dev: DeviceAccess):
        self.__transmitter = transmitter
        self.__dev = dev

    def get(self) -> float:
        return self.__dev.get()

    def set(self, value: float):
        self.__dev.set(value)

    def set_and_wait(self, value: float):
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        return self.__transmitter._cfg.voltage.unit()


# ------------------------------------------------------------------------------


class RWRFPhaseScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to cavity phase
    for a transmitter of a control system.
    """

    def __init__(self, transmitter: RFTransmitter, dev: DeviceAccess):
        self.__transmitter = transmitter
        self.__dev = dev

    def get(self) -> float:
        return self.__dev.get()

    def set(self, value: float):
        self.__dev.set(value)

    def set_and_wait(self, value: float):
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        return self.__transmitter._cfg.phase.unit()


# ------------------------------------------------------------------------------


class RWRFFrequencyScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to RF frequency of a control system.
    """

    def __init__(self, rf: RFPlant, dev: DeviceAccess):
        self.__rf = rf
        self.__dev = dev

    def get(self) -> float:
        # Serialized cavity has the same frequency
        return self.__dev.get()

    def set(self, value: float):
        self.__dev.set(value)

    def set_and_wait(self, value: float):
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        return self.__rf._cfg.masterclock.unit()


# ------------------------------------------------------------------------------


class RBetatronTuneArray(abstract.ReadFloatArray):
    """
    Class providing read write access to betatron tune of a control system.
    """

    def __init__(self, tune_monitor, devs: list[DeviceAccess]):
        self.__tune_monitor = tune_monitor
        self.__devs = devs

    def get(self) -> NDArray:
        # Return horizontal and vertical betatron tunes as a NumPy array
        return np.array(
            [
                self.__devs[0].get(),
                self.__devs[1].get(),
            ]
        )

    def unit(self) -> str:
        return self.__tune_monitor._cfg.tune_v.unit()
