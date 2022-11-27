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


# Resolve the location of the files
# TODO: check if there is another location the same file that takes precedence
def look_for_file(filename):
    file = pkg_resources.resource_filename('spynwave', 'data/' + filename)
    return file


config_file = look_for_file('config.yaml')
with open(config_file, 'r') as file:
    config = load(file, Loader)

# Prefix the remote visa prefix if remote accessing
config['general']['visa-prefix'] = ""
if config['general']['remote connection']:
    config['general']['visa-prefix'] = config['general']['remote visa-prefix']
