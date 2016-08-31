import yaml
import os

dir_path = os.path.dirname(os.path.realpath(__file__))
config = yaml.load(open("{}/../../config.yaml".format(dir_path), 'r'))
