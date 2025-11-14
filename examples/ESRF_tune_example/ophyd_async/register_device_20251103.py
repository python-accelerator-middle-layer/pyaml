#!/usr/bin/env python3
import os, tango

# Ensure TANGO_HOST is set in your shell (e.g., 127.0.0.1:10000)
print("TANGO_HOST =", os.environ.get("TANGO_HOST"))

db = tango.Database()

server = "simple_ds_20251103/instance1"
klass  = "SimpleDevice"
device = "test/simple/1"

# Create device info record
info = tango.DbDevInfo()
info.name   = device
info._class = klass
info.server = server

try:
    db.add_device(info)
    print("Registered device:", device, "on server:", server)
except Exception as e:
    if "already" in str(e).lower():
        print("Device already registered; continuing.")
    else:
        raise
