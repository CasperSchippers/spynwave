"""
This file is part of the SpynWave package.
"""

import logging
from time import sleep

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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def startup(self): pass
    def shutdown(self): pass
    def _set_field(self, field): pass
    def measure_field(self): pass

    def sweep_field(self, start, stop, ramp_rate, update_delay=0.1,
                    sleep_fn=lambda x: sleep(x), should_stop=lambda: False,
                    callback_fn=lambda x: True): pass

    def measurement_delay(self): pass
    def field_ramp_rate(self): pass
