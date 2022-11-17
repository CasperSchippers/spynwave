"""
This file is part of the SpynWave package.
"""

import logging

from spynwave.drivers.magnet_base import MagnetBase

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class MagnetOutOfPlane(MagnetBase):
    pass
