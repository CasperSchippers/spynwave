"""
This file is part of the SpynWave package.
"""

import logging

from spynwave.drivers.magnet_base import MagnetBase

# TODO: include the temperature controller, there is a python library from lakeshore for this

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class MagnetCryostat(MagnetBase):
    """ This class represents the magnet that is used on the crystat/blackhole spinwave setup.

    It uses a LakeShore 475 Gaussmeter and a LakeShore 643 Power Supply, which is controlled by the
    Gaussmeter. The setup also contains a LakeShore 336 Temperature Controller.

    """
    pass
