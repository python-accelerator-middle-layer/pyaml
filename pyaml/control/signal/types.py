from pydantic import BaseModel

class EpicsConfigR(BaseModel):
    read_pvname: str

class EpicsConfigW(BaseModel):
    write_pvname: str

class EpicsConfigRW(EpicsConfigR, EpicsConfigW):
    pass

class TangoConfigR(BaseModel):
    read_attr: str

class TangoConfigW(BaseModel):
    write_attr: str

class TangoConfigRW(TangoConfigR, TangoConfigW):
    pass

ControlSysConfig = (
    EpicsConfigR | EpicsConfigW | EpicsConfigRW |
    TangoConfigR | TangoConfigW | TangoConfigRW
)

