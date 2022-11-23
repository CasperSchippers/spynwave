"""
This file is part of the SpynWave package.
"""

from spynwave.constants import config

from spynwave.drivers.magnet_base import MagnetBase
from spynwave.drivers import MagnetInPlane, MagnetCryostat, MagnetOutOfPlane


class MagnetConstructor(type):
    def __call__(cls, *args, **kwargs):
        return cls.get_magnet_class()(*args, **kwargs)


class Magnet(type(MagnetBase), metaclass=MagnetConstructor):
    """ A constructor class that detects which magnet to use. This will never be
    actually instanced, since calling the class [Magnet()] will call the __call__ method
    of the MagnetConstructor metaclass and return an instance of the appropriate magnet
    class.
    """

    magnet_classes = {
        "in-plane magnet": MagnetInPlane,
        "out-of-plane magnet": MagnetOutOfPlane,
        "cryo magnet": MagnetCryostat,
    }

    @classmethod
    def get_magnet_class(cls):
        magnetclass = cls.magnet_classes[config["general"]["magnet"]]
        return magnetclass

