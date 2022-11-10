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
import u12  # LabJack library from labjackpython

# TODO: should be updated on pymeasure
from spynwave.pymeasure_patches.sm12013 import SM12013

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

address_power_supply = "visa://131.155.124.201/ASRL3::INSTR"
address_gauss_meter = "visa://131.155.124.201/ASRL9::INSTR"

labjack_settings = {
    "ID": 0,
    "voltage_channel": 1,
    "positive_polarity_bit": 2,
    "negative_polarity_bit": 1,
}
gauss_meter_setting = {
    "range": 3,  # tesla
    "fastmode": True,
    "autorange": "Software",  # "Hardware", "Software", "None"
    # Note: the hardware auto-range is terrible. Use autorange = "Software" for
    # a faster auto-ranging
    "fastmode_reading_frequency": 0.1,  # seconds,
    "normalmode_reading_frequency": 0.4,  # seconds,

}
calibration_file = "magnet_calibration.txt"


class Magnet:
    labjack = None
    power_supply = None
    gauss_meter = None

    cal_type = None
    cal_data = None

    max_current = 0
    max_voltage = 0
    current_ramp_rate = 0.5  # A/s
    max_current_step = 1  # A
    last_current = 0  # attribute to store the last applied current

    polarity = 0
    bitSelect_positive = 2**labjack_settings["positive_polarity_bit"]
    bitSelect_negative = 2**labjack_settings["negative_polarity_bit"]

    gauss_meter_ranges = [3., 0.3, 0.03, 0.003]
    gauss_meter_range_edges = [(0.25, 3.5), (0.025, 0.27), (0.0025, 0.027), (0, 0.0027)]
    gauss_meter_range = 0
    gauss_meter_software_adjust = gauss_meter_setting["autorange"] == "Software"
    gauss_meter_fast_mode = False

    @property
    def gauss_meter_delay(self):
        return {
            True: gauss_meter_setting["fastmode_reading_frequency"],
            False: gauss_meter_setting["normalmode_reading_frequency"]
        }[self.gauss_meter_fast_mode]

    def __init__(self):
        self.power_supply = SM12013(address_power_supply)
        self.clear_powersupply_buffer()
        self.max_current = self.power_supply.max_current
        self.max_voltage = self.power_supply.max_voltage

        self.labjack = u12.U12(id=labjack_settings["ID"])
        # Set the correct channels on the labjack to output channels for controlling the polarity
        self.labjack.digitalIO(
            trisD=self.bitSelect_positive + self.bitSelect_negative,
            trisIO=0,
            stateD=0,
            stateIO=0,
            updateDigital=True
        )

        self.gauss_meter = LakeShore421(address_gauss_meter)
        # self.gauss_meter.check_errors()

    def startup(self):
        self.load_calibration()

        ## Prepare current supply and labjack for magnetic field
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
        self.set_polarity(+1)

        ## Prepare the gauss meter
        # self.gauss_meter.id
        self.gauss_meter.unit = "T"
        self.gauss_meter_set_fast_mode(gauss_meter_setting["fastmode"])
        self.gauss_meter.auto_range = gauss_meter_setting["autorange"] == "Hardware"
        self.gauss_meter.field_range = gauss_meter_setting["range"]
        self.gauss_meter_range = self.gauss_meter.field_range_raw

    def load_calibration(self):
        # TODO: should make this less hardcoded and define standard format for table (with header)
        cal_data = pd.read_csv(calibration_file,
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

    def field_to_current(self, field):
        # Check if value within range of calibration
        if not self.cal_data["min_field"] <= field <= self.cal_data["max_field"]:
            raise ValueError(f"Field value ({field} T) out of bounds; should be between "
                             f"{self.cal_data['min_field']} T and {self.cal_data['max_field']} T "
                             f"(with the present calibration).")

        if self.cal_type == "interpolated lookup table":
            current = self.cal_data["B_to_I"](field)
        else:
            raise NotImplementedError(f"Current-field calibration type {self.cal_type} "
                                      f"not implemented.")

        self.check_current_within_bounds(current)

        return current

    def current_to_field(self, current):
        # Check if value within range of calibration
        if not self.cal_data["min_current"] >= current >= self.cal_data["max_current"]:
            raise ValueError(f"Current value ({current} A) out of bounds; should be between "
                             f"{self.cal_data['min_current']} A and {self.cal_data['max_current']} "
                             f"A (with the present calibration).")
        self.check_current_within_bounds(current)

        if self.cal_type == "interpolated lookup table":
            field = self.cal_data["I_to_B"](current)
        else:
            raise NotImplementedError(f"Current-field calibration type {self.cal_type} "
                                      f"not implemented.")

        return field

    def check_current_within_bounds(self, current):
        if abs(current) > self.max_current:
            raise ValueError(f"Current value ({current} A) out of bounds for power supply (maximum "
                             f"{self.max_current} A).")

    def set_field(self, field, controlled=True):
        """ Apply a specified magnetic field.

        :param field:  Field to apply in tesla.
        :param controlled: Boolean that controls the method for setting the current, if True a slow
            but safe and stable approach is used, if False a faster approach (for use in sweeps)
        """
        current = self.field_to_current(field)

        if controlled:
            self.ramp_current(current)
        else:
            self.set_current(current)

    def ramp_current(self, current):
        """ Apply a specified current by nicely ramping to this current. """
        polarity = self.current_polarity(current)

        if self.polarity_needs_changing(polarity):
            self.power_supply.ramp_to_zero(self.current_ramp_rate)
            self.last_current = 0
            self.set_polarity(polarity)

        self.power_supply.ramp_to_current(abs(current), self.current_ramp_rate)
        self.last_current = self.power_supply.current

    def set_current(self, current):
        """ Apply a specified current by instantly setting the current to the power supply.
        A few check are performed to ensure no breakage of the instruments.
        """
        if abs(abs(current) - abs(self.last_current)) > self.max_current_step:
            raise ValueError(f"Step in current too large: from {self.last_current} A to"
                             f"{abs(current)} A; maximum step-size is {self.max_current_step} A")

        polarity = self.current_polarity(current)
        if self.polarity_needs_changing(polarity):
            self.set_polarity(polarity)

        self.power_supply.current = abs(current)
        self.last_current = abs(current)

    @staticmethod
    def current_polarity(current):
        return int(math.copysign(1, current))

    def polarity_needs_changing(self, polarity):
        return polarity != self.polarity

    def set_polarity(self, polarity):
        if self.power_supply.current > self.max_current_step:
            self.power_supply.ramp_to_zero(self.current_ramp_rate)

        self.power_supply.disable()

        while not self.power_supply.measure_current == 0.:
            sleep(0.1)

        self.labjack_polarity_pulse(polarity)
        self.power_supply.enable()

    def labjack_polarity_pulse(self, polarity):
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

    def get_set_field(self):
        current = self.get_set_current()
        return self.current_to_field(current)

    def get_set_current(self):
        current = self.power_supply.current
        return self.polarity * current

    def sweep_field(self, start, stop, ramp_rate, update_delay=0.1,
                    sleep_fn=lambda x: sleep(x), should_stop=lambda: False,
                    callback_fn=lambda x: True):
        # Check if fields are within bounds
        self.field_to_current(start)
        self.field_to_current(stop)

        sweep_duration = abs((start - stop) / ramp_rate)
        number_of_updates = math.ceil(sweep_duration / update_delay)
        field_list = np.linspace(start, stop, number_of_updates + 1)

        for field in field_list:
            self.set_field(field, controlled=False)
            callback_fn(field)
            sleep_fn(update_delay)
            if should_stop():
                break

    def gauss_meter_set_fast_mode(self, enabled=True):
        self.gauss_meter.fast_mode = enabled
        sleep(0.4)
        self.gauss_meter_fast_mode = self.gauss_meter.fast_mode

    def measure_field(self):
        # First attempt at getting field
        field = self.gauss_meter.field

        # Simple case if no software adjustment is allowed
        if not self.gauss_meter_software_adjust:
            return field

        # Case if software adjustment is allowed.
        # If overloaded, try increasing the field range
        self.gauss_meter_range = self.gauss_meter.field_range_raw
        range_idx = self.gauss_meter_range
        if math.isnan(field):
            for range_idx in reversed(range(self.gauss_meter_range)):
                self.gauss_meter.field_range_raw = range_idx
                self.gauss_meter_range = range_idx
                sleep(self.gauss_meter_delay)
                field = self.gauss_meter.field
                if not math.isnan(field):
                    break
            else:  # return value (nan) if field remains overloaded in all ranges
                # self.gauss_meter_range = self.gauss_meter.field_range_raw
                return field

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
            log.info("Changed range: sleeping a full delay time")
            sleep(self.gauss_meter_delay)

        return field

    def wait_for_stable_field(self, tolerance=0.00025, timeout=None, should_stop=lambda: False):
        start = time()
        field = self.measure_field()
        while not should_stop() and not (timeout is not None and (time() - start) > timeout):
            if abs(field - (field := self.measure_field())) < tolerance:
                break

    def clear_powersupply_buffer(self):
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
