import yaml
import os

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
CONFIG = yaml.load(open("{}/../../config.yaml".format(DIR_PATH), 'r'))
DATA_DIR = '{}/../../data'.format(DIR_PATH)