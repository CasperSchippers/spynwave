"""
This file is part of the SpynWave package.
"""

import logging
import math
from time import time, sleep


from pymeasure.instruments.lakeshore import LakeShore421

from spynwave.constants import config
from spynwave.drivers.magnet_base import MagnetBase

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())


class LakeShore421Mixin(MagnetBase):
    gauss_meter_ranges = [3., 0.3, 0.03, 0.003]
    gauss_meter_range_edges = [(0.25, 3.5), (0.025, 0.27), (0.0025, 0.027), (0, 0.0027)]
    gauss_meter_range = 0
    gauss_meter_autorange = "None"
    gauss_meter_fast_mode = False

    measurement_delay = 0.4

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.gauss_meter_autorange = config[self.name]["gauss-meter"]["autorange"]

        self.gauss_meter = LakeShore421(
            config["general"]["visa-prefix"] + config[self.name]["gauss-meter"]["address"]
        )
        # self.gauss_meter.check_errors()

    def startup_lakeshore(self):
        # Prepare the gauss meter
        # self.gauss_meter.id
        self.gauss_meter.unit = "T"
        use_fast_mode = (self.measurement_type != "Frequency sweep" and
                         config[self.name]["gauss-meter"]["fastmode"])
        self._gauss_meter_set_fast_mode(use_fast_mode)
        self.gauss_meter.auto_range = self.gauss_meter_autorange == "Hardware"
        self.gauss_meter.field_range = config[self.name]["gauss-meter"]["range"]
        self.gauss_meter_range = self.gauss_meter.field_range_raw

    def shutdown_lakeshore(self):
        if self.gauss_meter is not None:
            self.gauss_meter.fast_mode = False
            self.gauss_meter.auto_range = True
            self.gauss_meter.shutdown()

    def _gauss_meter_set_fast_mode(self, enabled=True):
        self.gauss_meter.fast_mode = enabled
        sleep(0.4)
        self.gauss_meter_fast_mode = self.gauss_meter.fast_mode
        self.measurement_delay = {True: 0.1, False: 0.4}[self.gauss_meter_fast_mode]

    def measure_field(self):
        # First attempt at getting field
        field = self.gauss_meter.field

        # Simple case if no software adjustment is allowed
        if not self.gauss_meter_autorange == "Software":
            return field

        # Case if software adjustment is allowed.
        # If overloaded, try increasing the field range
        self.gauss_meter_range = self.gauss_meter.field_range_raw
        range_idx = self.gauss_meter_range
        if math.isnan(field):
            for range_idx in reversed(range(self.gauss_meter_range)):
                self.gauss_meter.field_range_raw = range_idx
                self.gauss_meter_range = range_idx
                sleep(self.measurement_delay)
                field = self.gauss_meter.field
                if not math.isnan(field):
                    break
            else:  # return value (nan) if field remains overloaded in all ranges
                # self.gauss_meter_range = self.gauss_meter.field_range_raw
                return field

        # If a non-nan field is measured, check if the gauss_meter ranges should be adjusted
        # Retrieve edges
        inner_edge, outer_edge = self.gauss_meter_range_edges[range_idx]

        # See if the range needs adjustment for the next measurement.
        if abs(field) > outer_edge:  # outer bound
            self.gauss_meter.field_range_raw = range_idx - 1
            # self.gauss_meter_range = range_idx - 1
        elif abs(field) < inner_edge:  # inner bound
            self.gauss_meter.field_range_raw = range_idx + 1
            # self.gauss_meter_range = range_idx + 1

        self.gauss_meter_range = self.gauss_meter.field_range_raw

        if range_idx != self.gauss_meter_range:
            # Ensure the next query is performed later, such that the field can settle
            log.info("Changed range: sleeping a full delay time")
            self.gauss_meter.last_write_time = time() + self.measurement_delay

        return field
