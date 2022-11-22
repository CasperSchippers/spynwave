"""
This file is part of the SpynWave package.
"""

from spynwave.constants import config

from spynwave.drivers.magnet_base import MagnetBase
from spynwave.drivers import MagnetInPlane, MagnetCryostat, MagnetOutOfPlane


class Magnet(MagnetBase):
    """ A constructor class that detects which magnet to use"""
    magnet_classes = {
        "in-plane magnet": MagnetInPlane,
        "out-of-plane magnet": MagnetOutOfPlane,
        "cryo magnet": MagnetCryostat,
    }

    def __new__(cls, *args, **kwargs):
        # Detect which magnet is used

        MagnetClass = cls.magnet_classes[config["general"]["magnet"]]

        return MagnetClass.__new__(*args, **kwargs)
