"""
This file is part of the SpynWave package.
"""

import logging
import math
from time import time, sleep

from pyvisa.errors import VisaIOError, VI_ERROR_TMO
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d

from pymeasure.instruments.lakeshore import LakeShore421
try:
    import u12  # LabJack library from labjackpython
except ImportError:
    u12 = None  # Happens if the dll is not installed

from spynwave.constants import config
from spynwave.drivers.magnet_base import MagnetBase

# TODO: should be updated on pymeasure
from spynwave.pymeasure_patches.sm12013 import SM12013

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())


class MagnetInPlane(MagnetBase):
    """ This class represents the magnet that is used on the crystat/blackhole spinwave setup.

    It uses a Delta-Elektronika SM120-13 unipolar power supply, router via a home-built switchbox
    (which is controlled using a labjack U12). The setup features a LakeShore 421 Gauss meter to
    probe the magnetic field.

    """
    name = "in-plane magnet"
    labjack = None

    max_current = config[name]["power-supply"]["max current"]
    max_voltage = config[name]["power-supply"]["max voltage"]
    current_ramp_rate = 0.5  # A/s
    max_current_step = 1  # A
    last_current = 0  # attribute to store the last applied current

    @property
    def field_ramp_rate(self):
        return self.current_ramp_rate * self.cal_data["max_field"] / self.cal_data["max_current"]

    polarity = 0
    bitSelect_positive = 2**config[name]["labjack"]["positive polarity bit"]
    bitSelect_negative = 2**config[name]["labjack"]["negative polarity bit"]

    gauss_meter_ranges = [3., 0.3, 0.03, 0.003]
    gauss_meter_range_edges = [(0.25, 3.5), (0.025, 0.27), (0.0025, 0.027), (0, 0.0027)]
    gauss_meter_range = 0
    gauss_meter_autorange = config[name]["gauss-meter"]["autorange"]
    gauss_meter_fast_mode = False

    @property
    def measurement_delay(self):
        return {
            True: config[self.name]["gauss-meter"]["fastmode reading frequency"],
            False: config[self.name]["gauss-meter"]["normalmode reading frequency"]
        }[self.gauss_meter_fast_mode]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.power_supply = SM12013(
            config["general"]["visa-prefix"] + config[self.name]["power-supply"]["address"]
        )
        self._clear_powersupply_buffer()
        self.max_current = self.power_supply.max_current
        self.max_voltage = self.power_supply.max_voltage

        self.labjack = u12.U12(id=config[self.name]["labjack"]["ID"])
        # Set the correct channels on the labjack to output channels for controlling the polarity
        self.labjack.digitalIO(
            trisD=self.bitSelect_positive + self.bitSelect_negative,
            trisIO=0,
            stateD=0,
            stateIO=0,
            updateDigital=True
        )

        self.gauss_meter = LakeShore421(
            config["general"]["visa-prefix"] + config[self.name]["gauss-meter"]["address"]
        )
        # self.gauss_meter.check_errors()

    def startup(self):
        self._load_calibration_from_file(config[self.name]["calibration file"])

        # Prepare current supply and labjack for magnetic field
        self.last_current = self.power_supply.current
        # self.power_supply.voltage
        # self.power_supply.ask("SE:DI:DA?")  # TODO: not sure what this does

        self.power_supply.ramp_to_zero(self.current_ramp_rate)
        self.power_supply.write("REM:CV")  # VS "LOC:CV"
        self.power_supply.write("REM:CC")  # VS "LOC:CC"

        self.power_supply.voltage = self.max_voltage
        self.power_supply.current = 0
        # TODO: the labview code does not use SO:FU:RSD but SO:FU:OUTP; see what the difference is
        # Now both are used in the enable and disable methods
        self.power_supply.enable()

        # Set polarity to positive
        self._set_polarity(+1)

        # Prepare the gauss meter
        # self.gauss_meter.id
        self.gauss_meter.unit = "T"
        use_fast_mode = (self.measurement_type != "Frequency sweep" and
                         config[self.name]["gauss-meter"]["fastmode"])
        self._gauss_meter_set_fast_mode(use_fast_mode)
        self.gauss_meter.auto_range = self.gauss_meter_autorange == "Hardware"
        self.gauss_meter.field_range = config[self.name]["gauss-meter"]["range"]
        self.gauss_meter_range = self.gauss_meter.field_range_raw

    def _load_calibration_from_file(self, file):
        # TODO: should make this less hardcoded and define standard format for table (with header)
        cal_data = pd.read_csv(file,
                               header=None,
                               names=["current", "field"],
                               delim_whitespace=True)

        # Ensure everything is in SI base units; should be automated/checked with the file
        cal_data.field *= 1e-3

        i_to_b = interp1d(cal_data.current, cal_data.field)
        b_to_i = interp1d(cal_data.field, cal_data.current)

        self.cal_type = "interpolated lookup table"
        self.cal_data = dict(
            data=cal_data,
            min_field=cal_data.field.min(),
            max_field=cal_data.field.max(),
            min_current=cal_data.current.min(),
            max_current=cal_data.current.max(),
            I_to_B=i_to_b,
            B_to_I=b_to_i,
        )

    def _set_field(self, field, controlled=True):
        """ Apply a specified magnetic field.

        :param field:  Field to apply in tesla.
        :param controlled: Boolean that controls the method for setting the current, if True a slow
            but safe and stable approach is used, if False a faster approach (for use in sweeps)

        :return field: Returns the applied field
        """

        current = self._field_to_current(field)

        if controlled:
            self._ramp_current(current)
        else:
            self._set_current(current)

        return field

    def _ramp_current(self, current):
        """ Apply a specified current by nicely ramping to this current. """
        polarity = self._current_polarity(current)

        if self._polarity_needs_changing(polarity):
            self.power_supply.ramp_to_zero(self.current_ramp_rate)
            self.last_current = 0
            self._set_polarity(polarity)

        self.power_supply.ramp_to_current(abs(current), self.current_ramp_rate)
        self.last_current = self.power_supply.current

    def _set_current(self, current):
        """ Apply a specified current by instantly setting the current to the power supply.
        A few check are performed to ensure no breakage of the instruments.
        """
        if abs(abs(current) - abs(self.last_current)) > self.max_current_step:
            raise ValueError(f"Step in current too large: from {self.last_current} A to"
                             f"{abs(current)} A; maximum step-size is {self.max_current_step} A")

        polarity = self._current_polarity(current)
        if self._polarity_needs_changing(polarity):
            self._set_polarity(polarity)

        self.power_supply.current = abs(current)
        self.last_current = abs(current)

    @staticmethod
    def _current_polarity(current):
        return int(math.copysign(1, current))

    def _polarity_needs_changing(self, polarity):
        return polarity != self.polarity

    def _set_polarity(self, polarity):
        if self.power_supply.current > self.max_current_step:
            self.power_supply.ramp_to_zero(self.current_ramp_rate)

        self.power_supply.disable()

        while not self.power_supply.measure_current == 0.:
            sleep(0.1)

        self._labjack_polarity_pulse(polarity)
        self.power_supply.enable()

    def _labjack_polarity_pulse(self, polarity):
        self.labjack.pulseOut(
            bitSelect=self.bitSelect_positive if polarity >= 0 else self.bitSelect_negative,
            numPulses=1,
            timeB1=250,  # Pulse length (~us)
            timeC1=1,
            timeB2=1,
            timeC2=1,
            lowFirst=False,
        )
        self.polarity = polarity

    def _get_set_field(self):
        current = self._get_set_current()
        return self._current_to_field(current)

    def _get_set_current(self):
        current = self.power_supply.current
        return self.polarity * current

    def sweep_field(self, start, stop, ramp_rate, update_delay=0.1,
                    sleep_fn=lambda x: sleep(x), should_stop=lambda: False,
                    callback_fn=lambda x: None):
        # Check if fields are within bounds
        self._field_to_current(start)
        self._field_to_current(stop)

        sweep_duration = abs((start - stop) / ramp_rate)
        number_of_updates = math.ceil(sweep_duration / update_delay)
        field_list = np.linspace(start, stop, number_of_updates + 1)

        for field in field_list:
            self.set_field(field, controlled=False)
            callback_fn(field)
            sleep_fn(update_delay)
            if should_stop():
                break

    def _gauss_meter_set_fast_mode(self, enabled=True):
        self.gauss_meter.fast_mode = enabled
        sleep(0.4)
        self.gauss_meter_fast_mode = self.gauss_meter.fast_mode

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

    def _clear_powersupply_buffer(self):
        timeout = self.power_supply.adapter.connection.timeout
        try:
            self.power_supply.adapter.connection.timeout = 10
            while True:
                log.debug(self.power_supply.adapter.read())
        except VisaIOError as exc:
            if not exc.error_code == VI_ERROR_TMO:
                raise exc
        finally:
            self.power_supply.adapter.connection.timeout = timeout

    def shutdown(self):
        if self.power_supply is not None:
            self.power_supply.shutdown()

        # TODO: shutdown labjack?

        if self.gauss_meter is not None:
            self.gauss_meter.fast_mode = False
            self.gauss_meter.auto_range = True
            self.gauss_meter.shutdown()
