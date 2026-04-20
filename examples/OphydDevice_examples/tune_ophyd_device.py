import asyncio
from typing import TypedDict

import numpy as np
from ophyd_async.core import DerivedSignalFactory, StandardReadable, Transform
from ophyd_async.epics.core import epics_signal_r
from pydantic import BaseModel

from pyaml.accelerator import Accelerator
from pyaml.common.abstract import ReadFloatArray
from pyaml.common.element import Element
from pyaml.control.controlsystem import ControlSystemAdapter
from pyaml.diagnostics.atune_monitor import ABetatronTuneMonitor

evloop = None


class MyControlSystemConfigModel(BaseModel):
    name: str
    prefix: str
    view: str


class MyControlSystem(ControlSystemAdapter):
    def __init__(self, cfg: MyControlSystemConfigModel):
        ControlSystemAdapter.__init__(self)
        self._cfg = cfg

    def name(self) -> str:
        return self._cfg.name

    def prefix(self) -> str:
        return self._cfg.prefix

    def view(self) -> str:
        return self._cfg.view


class TuneDerived(TypedDict):
    frequency: float
    tune: float


class TuneTransform(Transform):
    revolution_frequency: float
    hardware_view: bool

    def raw_to_derived(self, *, signal: float) -> TuneDerived:
        if self.hardware_view:
            frequency = signal * 1e3
            tune = frequency / self.revolution_frequency
        else:
            tune = signal
            frequency = tune * self.revolution_frequency * 1e3

        return TuneDerived(frequency=frequency, tune=tune)


class Tune1D(StandardReadable):
    """Device to read tune in one dimension."""

    def __init__(
        self,
        peer: "MyTuneMonitor",
        cs: "MyControlSystem",
        name: str,
    ):
        native = epics_signal_r(float, name)
        self._factory = DerivedSignalFactory(
            TuneTransform, signal=native, revolution_frequency=peer.frev, hardware_view=cs.view() == "HARDWARE"
        )

        if cs.view() == "HARDWARE":
            frequency = native
            tune = self._factory.derived_signal_r(float, "tune")
        else:
            tune = native
            frequency = self._factory.derived_signal_r(float, "frequency")

        with self.add_children_as_readables():
            self.tune = tune
            self.frequency = frequency

        super().__init__(name=name)


class MyTuneMonitor(Element, ABetatronTuneMonitor, StandardReadable):
    def __init__(self, name: str, cs: MyControlSystem, device_h: str, device_v: str, frev: float):
        Element.__init__(self, name)
        self.frev = frev
        tune_h = Tune1D(self, cs, cs.prefix() + device_h)
        tune_v = Tune1D(self, cs, cs.prefix() + device_v)
        with self.add_children_as_readables():
            self.hor = tune_h
            self.ver = tune_v
        StandardReadable.__init__(self, name=name)

    def arun(self, coro):
        return evloop.run_until_complete(coro)

    async def read_tune(self):
        await self.connect()
        req = [self.hor.tune.get_value(), self.ver.tune.get_value()]
        return await asyncio.gather(*req)

    async def read_tunefreq(self):
        await self.connect()
        req = [self.hor.frequency.get_value(), self.ver.frequency.get_value()]
        return await asyncio.gather(*req)

    @property
    def frequency(self) -> ReadFloatArray:
        class TuneFreqReader(ReadFloatArray):
            def __init__(self, parent: MyTuneMonitor):
                self.parent = parent

            def get(self) -> np.array:
                return self.parent.arun(self.parent.read_tunefreq())

            def unit(self) -> str:
                return "Hz"

        return TuneFreqReader(self)

    @property
    def tune(self) -> ReadFloatArray:
        class TuneReader(ReadFloatArray):
            def __init__(self, parent: MyTuneMonitor):
                self.parent = parent

            def get(self) -> np.array:
                return self.parent.arun(self.parent.read_tune())

            def unit(self) -> str:
                return "1"

        return TuneReader(self)


acc_config = {
    "type": "pyaml.accelerator",
    "facility": "BESSY2",
    "machine": "sr",
    "energy": 1.7185e9,
    "data_folder": "/data/store",
    "controls": [
        {
            "type": MyControlSystem.__module__,
            "class": "MyControlSystem",
            "validation_class": "MyControlSystemConfigModel",
            "prefix": "pons:",
            "name": "live",
            "view": "HARDWARE",
        }
    ],
    "devices": [
        {
            "type": MyTuneMonitor.__module__,
            "class": "MyTuneMonitor",
            "name": "MY_TUNE_MONITOR",
            "control_modes": ["live"],
            "device_h": "TUNEZR:rdH",
            "device_v": "TUNEZR:rdV",
            "frev": 1.25e6,
        }
    ],
}

# Launch event loop
evloop = asyncio.new_event_loop()
asyncio.set_event_loop(evloop)

# Main code
sr = Accelerator.from_dict(acc_config)
tm1 = sr.live.get_betatron_tune_monitor("MY_TUNE_MONITOR")
print(tm1.tune.get())
print(tm1.frequency.get())
