"""
This file is part of the SpynWave package.
"""

import logging

from spynwave.drivers.magnet_base import MagnetBase

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class MagnetOutOfPlane(MagnetBase):
    """ This class represents the magnet that is used on the out-of-plane spinwave setup.

    It uses a Bruker B-MN 45/60 Power Supply, controlled by a Bruker B-EC1 controller.
    To manually apply a current, turn on the power supply (big red switch), then turn on the
    controller; if the input-key (physical key) is set to local, the output can be enabled by
    pressing "DC", followed by "set". Using the "cur" button (maybe the "set") the current can be
    controlled using the knob.

    """
    pass
