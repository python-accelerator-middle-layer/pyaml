pyAML documentation
===================

Introduction
------------

python Accelerator Middle Layer (pyAML) is a joint technology platform to develop common tools for control, tuning and development of storage rings, beam transport lines and linear accelerators.

With pyAML, it WILL be possible to (the software is at conceptualization stage):

- **get/set instruments attributes**: such as strengths of magnets and positions from BPMS
- **use the same tuning tools in any facility using pyAML**,
- **compare data to it's digital twin equivalent**,
- **compute statistical properties for several lattice instances with errors**
- **flexible complex unit conversions**
- **easy and friendly configuration**
- many more features

Installation
------------
pip support will be provided later.
for the time being:

git clone https://github.com/python-accelerator-middle-layer/pyaml.git


Documentation
-------------

.. toctree::
   :maxdepth: 1

   How to/Load a configuration file <notebooks/load_configuration>
   How to/Switch design live <notebooks/live_design>
   How to/Select a control system <notebooks/control_system>
   How to/Arrays <notebooks/arrays>

   api

.. .. toctree::
..     :maxdepth: 1
..     :caption: How to:
..     :glob:

..     Load a configuration file <notebooks/load_configuration>
..     Switch design live <notebooks/live_design>
..     Select a control system <notebooks/control_system>
..     Arrays <notebooks/arrays>

.. .. toctree::
..    :caption: Modules:
..    :maxdepth: 1
..    :glob:

..    modules/*


Collaboration community
------------------------

Discussion
~~~~~~~~~~

`Mattermost <https://mattermost.hzdr.de/accelerator-middle-layer/channels/town-square>`_

(please log in using Helmoltz ID, you will be prompt to access with your own lab/university credentials)

Shared documents
~~~~~~~~~~~~~~~~

to access the shared documents please ask S.Liuzzo for access rigths.

The pyAML "software requirement specification" document is visible here:
https://www.overleaf.com/read/hnrqzhfpbvpp#ef8935

to be added to editors list please write to S.Liuzzo

Mailing list:
~~~~~~~~~~~~~
to be added to the pyAML mailing list please write to S.Liuzzo



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
