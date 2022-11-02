"""
This file is part of the spynwave package.

This package provides software for performing propagating spinwave spectroscopy measurements
in the PSWS setups at FNA.

"""
import warnings

from importlib.metadata import version, PackageNotFoundError
try:
    __version__ = version("spynwave")
except PackageNotFoundError:
    warnings.warn('Could not find spynwave version, it does not seem to be installed. '
                  'Install it (editable or full)')
    __version__ = '0.0.0'
finally:
    del version, PackageNotFoundError
