#!/usr/bin/env python
# coding: utf-8

# In[1]:


# ## Facility configuration
#
# Edit the `CONFIG_FILE` variable below to select the facility. The rest of the notebook runs unchanged.
#
# | Facility | Config file | Control system | Virtual twin |
# |----------|-------------|----------------|--------------|
# | SOLEIL II | `config/soleil_ii/p.yaml` | TANGO (`tango-pyaml`) | Apptainer container |
# | BESSY2 | `config/bessy2/bessy2.yaml` | EPICS (`pyaml-cs-oa`) | Apptainer container |
# | ESRF EBS | `config/esrf/esrf.yaml` | TANGO (`tango-pyaml`) | Apptainer container |
#
# See `README.md` for installation and virtual accelerator startup instructions.
# In[2]:
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from pyaml.accelerator import Accelerator
from pyaml.common.constants import Action

# ── Facility configuration ──────────────────────────────────────────────────
# Uncomment the facility you want to use:

# CONFIG_FILE = "config/soleil_ii/p.yaml"
# CONFIG_FILE = "config/bessy2/bessy2.yaml"
CONFIG_FILE = "config/esrf/esrf.yaml"
# ────────────────────────────────────────────────────────────────────────────

CONFIG_DIR = Path(CONFIG_FILE).parent

sr = Accelerator.load(CONFIG_FILE)
print(sr)  # string representation


# ### Virtual accelerator setup
#
# For **live** control mode you need a running control system or emulator.
# If you want to skip this, run the notebook in **design** mode only.
#
# **SOLEIL II / ESRF (TANGO)**
# ```
# apptainer pull virtual-accelerator.sif oras://gitlab-registry.synchrotron-soleil.fr/software-control-system/containers/apptainer/virtual-accelerator:latest
# apptainer run virtual-accelerator.sif
# ```
#
# **BESSY2 (EPICS)**
# ```
# apptainer run oras://registry.hzdr.de/digital-twins-for-accelerators/containers/pyat-softioc-digital-twin:default-v0-5-1-bessy.2711893
# ```
#
# > **Note for BESSY2 live mode:** the PV prefix in `config/bessy2/bessy2.yaml` must match
# > your virtual accelerator instance. Edit the `prefix:` field under `controls:`.

# ### Control mode choice
#
# - **`sr.design`** — runs pyAT locally, no control system needed. Set `wait_time = 0.0`.
# - **`sr.live`** — connects to the real machine or virtual twin. Set `wait_time` to allow
#   readback settling (typically 1.5–2 s).

# In[3]:


SR = sr.design
# SR = sr.live

wait_time = 0.0 if SR == sr.design else 2.0
print(SR)  # string representation


# #### Betatron tune monitor
#
# The tune monitor is defined in the configuration file under the name `BETATRON_TUNE`.

# In[4]:


tune_monitor = SR.get_betatron_tune_monitor("BETATRON_TUNE")
print(f"Current tune: {tune_monitor.tune.get()}")
print(tune_monitor)  # string representation


# #### Quadrupolar correctors
#
# The `QForTune` array contains the quadrupoles used for tune correction.
# You can access and set individual corrector strengths.

# In[5]:


qcorrectors = SR.get_magnets("QForTune")
first_q = qcorrectors[0]
print(f"The ring has {len(qcorrectors)} quadrupolar correctors. First: {first_q.get_name()}")
print(qcorrectors[0])  # string representation


# In[6]:


str_before = qcorrectors[0].strength.get()
print(f"Current strength: {qcorrectors[0].strength.get()=:.4f}")
qcorrectors[0].strength.set(str_before + 0.002)
print(f"After stepping by 0.002: {qcorrectors[0].strength.get()=:.4f}")
qcorrectors[0].strength.set(str_before)
print(f"Reset to {str_before:.4f}")


# ### Standard tune correction tool
#
# `SR.tune` is the `DEFAULT_TUNE_CORRECTION` tool. `SR.trm` is the `DEFAULT_TUNE_RESPONSE_MATRIX` tool.
#
# Before correcting the tune you need a response matrix. It can be measured (below) or loaded from a previously saved file.

# In[7]:


print(SR.tune)  # string representation


# #### Measuring the tune response matrix
#
# The callback below prints progress during the measurement. The `sleep_between_step`
# parameter controls the wait time between corrector steps — set it to 0 for design mode.
#
# > **Note:** on some lattices `disable_6d()` is required before measuring in design mode.

# In[8]:


# Required on some lattices before measuring the TRM in design mode
sr.design.get_lattice().disable_6d()


def tune_callback(action: int, cb_data: dict):
    if action == Action.MEASURE:
        print(f"Tune response: #{cb_data['step']} {cb_data['magnet']} {cb_data['tune']}")
    return True


# In[9]:


if SR.tune.response_matrix is None:
    SR.trm.measure(sleep_between_step=wait_time, callback=tune_callback)
    SR.trm.save(CONFIG_DIR / "trm.json")

SR.tune.load(CONFIG_DIR / "trm.json")
print("Response matrix loaded.")
print(SR.trm)  # string representation


# #### Correcting the tune
#
# `SR.tune.set([qx, qy])` runs the correction iteratively. The `iter` parameter controls
# the number of iterations and `wait_time` the settling time between each iteration.

# In[10]:


print(f"Tune before correction: {SR.tune.readback()}")

qx, qy = 0.19, 0.28
print(f"\nSetting tune to [{qx}, {qy}]")
SR.tune.set([qx, qy], iter=10, wait_time=wait_time)
print(f"Tune after correction: {SR.tune.readback()}")

qx, qy = 0.21, 0.30
print(f"\nSetting tune to [{qx}, {qy}]")
SR.tune.set([qx, qy], iter=10, wait_time=wait_time)
print(f"Tune after correction: {SR.tune.readback()}")

print(SR.tune)  # string representation


# In[ ]:
