import yaml

from pyaml.configuration.factory import Factory

cc = yaml.safe_load(open("templated_config.yaml"))

obj = Factory.build(cc)
print(obj)
