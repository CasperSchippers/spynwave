"""
This file is part of the SpynWave package.

This file takes care of defining constants that are used throughout the software. This includes e.g.
the addresses of instruments, default properties for some instruments, and calibration-files.
"""

import pkg_resources
from pathlib import Path

from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


# Resolve the location of the files
# TODO: check if there is another location the same file that takes precedence
def look_for_file(filename):
    """ Look for a file with filename in different folders, first it will look in the present
    working directory, in the spynwave directory in the user home folder. If it cannot find the file
    in one of these locations, it will look for the file in the internal packaged data folder.
    """
    search_directories = [
        Path().absolute(),  # Current working directory
        Path.home() / "spynwave",  # Spynwave folder in user home directory
        Path(pkg_resources.resource_filename('spynwave', 'data/')),  # Package data folder
    ]

    for directory in search_directories:
        if directory.exists() and (directory / filename).is_file():
            return directory / filename

    raise FileNotFoundError(f"Could not find a file called {filename} in any of the searching "
                            f"directories: {'; '.join(str(d) for d in search_directories)}")


config_file = look_for_file('config.yaml')
with open(config_file, 'r') as file:
    config = load(file, Loader)

# Prefix the remote visa prefix if remote accessing
config['general']['visa-prefix'] = ""
if config['general']['remote connection']:
    config['general']['visa-prefix'] = config['general']['remote visa-prefix']
