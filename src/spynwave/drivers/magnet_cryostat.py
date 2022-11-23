"""
This file is part of the SpynWave package.
"""

import logging
from time import sleep

from spynwave.pymeasure_patches.lakeshore475 import LakeShore475

from spynwave.constants import config
from spynwave.drivers.magnet_base import MagnetBase

# TODO: include the temperature controller, there is a python library from lakeshore for this

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class MagnetCryostat(MagnetBase):
    """ This class represents the magnet that is used on the crystat/blackhole spinwave setup.

    It uses a LakeShore 475 Gaussmeter and a LakeShore 643 Power Supply, which is controlled by the
    Gaussmeter. The setup also contains a LakeShore 336 Temperature Controller.

    """
    name = "cryo magnet"

    max_field = config[name]["max field"]
    field_ramp_rate = config[name]["ramp rate"]

    measurement_delay = config[name]["gauss-meter"]["reading frequency"]
    gauss_meter_autorange = config[name]["gauss-meter"]["autorange"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.gauss_meter = LakeShore475(
            config['general']['visa-prefix'] + config[self.name]['power-supply']['address']
        )

    def startup(self, measurement_type=None):
        if not self.gauss_meter.field_control_enabled:
            self.gauss_meter.field_setpoint = 0

            self.gauss_meter.field_control_enabled = True

        self.gauss_meter.unit = "T"
        self.gauss_meter.auto_range = self.gauss_meter_autorange == "Hardware"
        self.gauss_meter.field_range = config[self.name]["gauss-meter"]["range"]

    def shutdown(self):
        self.gauss_meter.field_setpoint = 0
        self.gauss_meter.field_control_enabled = False

    def _set_field(self, field):
        self.gauss_meter.field_setpoint = field

        return field

    def measure_field(self):
        # TODO: look at the high speed binary field readings (RDGFAST?)
        return self.gauss_meter.field

    def sweep_field(self, start, stop, ramp_rate, update_delay=0.1,
                    sleep_fn=lambda x: sleep(x), should_stop=lambda: False,
                    callback_fn=lambda x: True):
        # Set the ramp-rate in T/minute
        self.gauss_meter.field_ramp_rate = ramp_rate * 60.

        # Start ramping (start field is not used)
        self.gauss_meter.field_setpoint = stop

        # Check if still ramping
        # TODO: see how we can also use the callback_fn, maybe using the start-stop
        while self.gauss_meter.field_setpoint_ramping and not should_stop():
            sleep_fn(update_delay)

        if not should_stop():
            self.wait_for_stable_field()
