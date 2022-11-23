"""
This file is part of the SpynWave package.
"""

import logging
import math
from time import time, sleep

import numpy as np

from spynwave.pymeasure_patches.brukerBEC1 import BrukerBEC1

from spynwave.constants import config
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

    When turning on the DC-output, there is a chance to trigger the fuse the magnet is connected to.

    """
    name = "out-of-plane magnet"

    max_field = config[name]["max field"]

    max_current = config[name]["power-supply"]["max current"]
    max_voltage = config[name]["power-supply"]["max voltage"]
    current_ramp_rate = config[name]["power-supply"]["max ramp rate"]

    measurement_delay = config[name]["gauss-meter"]["reading frequency"]  # TODO: move to gauss part

    field_ramp_rate = current_ramp_rate * max_field / max_current

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.power_supply = BrukerBEC1(
            config['general']['visa-prefix'] + config[self.name]['power-supply']['address']
        )

    def startup(self):
        if not self.power_supply.DC_power_enabled:
            log.warning("Enabling the DC output of the power supply. Be alerted that this can"
                        "potentially trip the fuse.")
            self.power_supply.current = 0
            sleep(0.1)
            self.power_supply.DC_power_enabled = True
            sleep(0.2)

    def shutdown(self):
        # Due to the chance to trip the fuse, the supply is not disabled, but just ramped down.
        self._set_current(0)

    def _set_field(self, field):
        current = self._field_to_current(field)
        self._set_current(current)
        return field

    def _set_current(self, current):
        self.power_supply.current = current

    def measure_field(self):
        # TODO: Implement gauss meter
        return self._current_to_field(self.power_supply.output_current)

    def sweep_field(self, start, stop, ramp_rate, update_delay=0.2,
                    sleep_fn=lambda x: sleep(x), should_stop=lambda: False,
                    callback_fn=lambda x: True):

        # Check if fields are within bounds
        self._field_to_current(start)
        self._field_to_current(stop)

        sweep_duration = abs((start - stop) / ramp_rate)
        number_of_updates = math.ceil(sweep_duration / update_delay)

        field_list = np.linspace(start, stop, number_of_updates + 1)

        t0 = 0
        for field in field_list:
            if (delay := update_delay + (t0 - time())) > 0:
                sleep_fn(delay)
            else:
                log.debug(f"Setting field took {-delay} longer than update delay "
                          f"({update_delay - delay}s vs {update_delay} s")
            t0 = time()

            self.set_field(field)
            callback_fn(field)
            if should_stop():
                break
