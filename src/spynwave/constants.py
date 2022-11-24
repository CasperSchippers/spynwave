"""
This file is part of the SpynWave package.

This file takes care of defining constants that are used throughout the software. This includes e.g.
the addresses of instruments, default properties for some instruments, and calibration-files.
"""

import pkg_resources

from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

# In the data-path, there are default/sample files
DATA_PATH = pkg_resources.resource_filename('spynwave', 'data/')

DEFAULT_CONFIG_FILE = pkg_resources.resource_filename('spynwave', 'data/config.yaml')

# TODO: check if there is another config file:
with open(DEFAULT_CONFIG_FILE, 'r') as configfile:
    config = load(configfile, Loader)

# Prefix the remote visa prefix if remote accessing
config['general']['visa-prefix'] = ""
if config['general']['remote connection']:
    config['general']['visa-prefix'] = config['general']['remote visa-prefix']


# Resolve the location of the files
# TODO: check if there is another location the same file that takes precedence
def look_for_file(filename):
    file = pkg_resources.resource_filename('spynwave', 'data/' + filename)
    return file
