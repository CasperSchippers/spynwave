"""
This file is part of the SpynWave package.
"""

import logging
import math
from time import time, sleep

import numpy as np

from spynwave.constants import config
from spynwave.drivers.magnet_base import MagnetBase
from spynwave.drivers.magnet_lakeshore421 import LakeShore421Mixin

from spynwave.pymeasure_patches.brukerBEC1 import BrukerBEC1


log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class MagnetOutOfPlane(LakeShore421Mixin, MagnetBase):
    """ This class represents the magnet that is used on the out-of-plane spinwave setup.

    It uses a Bruker B-MN 45/60 Power Supply, controlled by a Bruker B-EC1 controller.

    To manually apply a current, turn on the power supply (big red switch), then turn on the
    controller; if the input-key (physical key) is set to local, the output can be enabled by
    pressing "DC", followed by "set". Using the "cur" button (maybe the "set") the current can be
    controlled using the knob.

    When turning on the DC-output, there is a chance to trigger the fuse the magnet is connected to.

    The setup features a Lakeshore 421 Gauss Meter for measuring the field

    """
    name = "out-of-plane magnet"

    max_field = config[name]["max field"]

    max_current = config[name]["power-supply"]["max current"]
    max_voltage = config[name]["power-supply"]["max voltage"]
    current_ramp_rate = config[name]["power-supply"]["max ramp rate"]

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

        self.startup_lakeshore()

    def shutdown(self):
        # Due to the chance to trip the fuse, the supply is not disabled, but just ramped down.
        self._set_current(0)

        self.shutdown_lakeshore()

    def _set_current(self, current, **kwargs):
        if kwargs:
            log.warning(f"Method _set_current does not support these kwargs: {kwargs}.")

        self.power_supply.current = current
        return current

    # def measure_field(self):
    #     """ Measure the field by querying the output current. Superseded by a gauss-meter
    #     measurement.
    #     """
    #     return self._current_to_field(self.power_supply.output_current)

    def sweep_field(self, start, stop, ramp_rate, update_delay=0.1,
                    sleep_fn=lambda x: sleep(x), should_stop=lambda: False,
                    callback_fn=lambda x: True):

        self.power_supply.current_check_set_errors = False
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

        self.power_supply.current_check_set_errors = True
