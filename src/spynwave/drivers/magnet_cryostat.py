"""
This file is part of the SpynWave package.
"""

import logging

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
    gauss_meter_autorange = config["cryo magnet"]["gauss-meter"]["autorange"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.gauss_meter = LakeShore475(
            config['general']['visa-prefix'] + config['in-plane magnet']['power-supply']['address']
        )

    @property
    def measurement_delay(self):
        return config["cryo magnet"]["gauss-meter"]["reading frequency"]

    field_ramp_rate = config["cryo magnet"]["ramp rate"]

    def startup(self, measurement_type=None):
        if not self.gauss_meter.field_control_enabled:
            self.gauss_meter.field_setpoint = 0

            self.gauss_meter.field_control_enabled = True

        self.gauss_meter.unit = "T"
        self.gauss_meter.auto_range = self.gauss_meter_autorange == "Hardware"
        self.gauss_meter.field_range = config["in-plane magnet"]["gauss-meter"]["range"]

    def shutdown(self):
        self.gauss_meter.field_setpoint = 0
        self.gauss_meter.field_control_enabled = False

    def set_field(self, field):
        if self.mirror_fields:
            field *= -1

        self.gauss_meter.field_setpoint = 0

        return field

    def measure_field(self):
        # TODO: look at the high speed binary field readings (RDGFAST?)
        return self.gauss_meter.field

    # sweep_field
    # wait_for_stable_field


