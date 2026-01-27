Run the BESSY va:

```bash
apptainer run oras://registry.hzdr.de/digital-twins-for-accelerators/containers/pyat-softioc-digital-twin:default-v0-5-1-bessy.2711893
```

Run the epics tools:
```bash
apptainer run oras://registry.hzdr.de/digital-twins-for-accelerators/epics-tools:v0-1-0.2028728
```

In the epics tools:
```bash
epics tools ~/Desktop > pvlist
GUID 0x4A709B99A866F1326CBBE22F version 2: tcp@[ 160.103.10.135:5075 ]
epics tools ~/Desktop > pvlist 0x4A709B99A866F1326CBBE22F
pons:CAVH1T8R:freq
pons:CAVH2T8R:freq
...
```

Edit your yaml config file and setup the control system prefix:
```yaml
controls:
  - type: pyaml_cs_oa.controlsystem
    prefix: "your_prefix:"
    name: live
```

Run the exmaples
