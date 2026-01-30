# Instructions for how to run the ESRF Tune example.

## Install pyAML

1. Create a virtual environment and activate it. It needs to have >= Python 3.11.

2. Install pyAML including the tango bindings.

  ```bash
  pip install accelerator-middle-layer[tango]
  ```

3. install EBS dummy Control system. This is valid untill an ESRF virtual machine will be available as for BESSYII and SOLEIL
   ```bash
   pip install tests/dummy_cs/tango-pyaml
   ```

  ## Run the examples

  1. navigate to the pyaml root directory 
  1. Download (or clone) the example files. 

  ## expected output for SR.design is

  30 Jan 2026, 09:23:13 | WARNING | PyAML Tango control system binding (0.3.2) initialized with name 'live' and TANGO_HOST=ebs-simu-3:10000
  Tune response: #0 QD2E-C04 [ 0.17851726 -1.25993589]
  Tune response: #1 QD2A-C05 [ 0.17889514 -1.25969115]
  ...
  Tune response: #123 QF1A-C03 [ 0.59069308 -0.49430245]
  Initial tune: [0.16000001 0.33999986]
  Final tune: [0.17 0.32]


  ## expected output for SR.live is
  Initial tune: [0. 0.]
  MultiAttribute.get(124 values)
  MultiAttribute.get(124 values)
  MultiAttribute.set(124 values)
  //ebs-simu-3:10000/srmag/vps-qd2/c04-e/current:0.8688600876142427
  ...
  //ebs-simu-3:10000/srmag/vps-qf1/c02-e/current:1.3024074153237937
  //ebs-simu-3:10000/srmag/vps-qf1/c03-a/current:1.2966875742108155
  Final tune: [0. 0.]