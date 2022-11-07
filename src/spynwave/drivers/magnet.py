"""
This file is part of the SpynWave package.
"""

import math
from time import sleep
import pandas as pd
from scipy.interpolate import interp1d

# TODO: should be updated on pymeasure
from spynwave.pymeasure_patches.sm7045d import SM7045D

import u12  # LabJack library from labjackpython

address_magnet = "ASRL3::INSTR"

labjack_settings = {
    "ID": 0,
    "voltage_channel": 1,
    "positive_polarity_bit": 2,
    "negative_polarity_bit": 1,
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
    current_ramp_rate = 0.2  # A/s
    max_current_step = 0.5  # A
    last_current = 0  # attribute to store the last applied current

    polarity = 0
    bitSelect_positive = 2**labjack_settings["positive_polarity_bit"]
    bitSelect_negative = 2**labjack_settings["negative_polarity_bit"]

    def __init__(self):
        self.power_supply = SM7045D(address_magnet)
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

    def startup(self):
        self.load_calibration()

        self.last_current = self.power_supply.current
        # self.power_supply.voltage
        # self.power_supply.ask("SE:DI:DA?")  # TODO: not sure what this does

        self.power_supply.ramp_to_zero(self.current_ramp_rate)
        self.power_supply.ask("REM:CV")  # VS "LOC:CV"
        self.power_supply.ask("REM:CC")  # VS "LOC:CC"

        self.power_supply.voltage = self.max_voltage
        self.power_supply.current = 0
        self.power_supply.enable()  # TODO: the labview code does not use SO:FU:RSD but SO:FU:OUTP
        self.power_supply.write("SO:FU:OUTP 1")

        # Set polarity to positive
        self.set_polarity(+1)

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
        if not self.cal_data["min_field"] < field < self.cal_data["max_field"]:
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
        if not self.cal_data["min_current"] > current > self.cal_data["max_current"]:
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

    def set_field(self, field, method="ramp"):
        """ Apply a specified magnetic field.

        :param field:  Field to apply in tesla.
        :param method: Method for setting the current, options are "ramp" for a slow but safe and
            stable approach, or "set" for a faster approach (for use in sweeps)
        """
        current = self.field_to_current(field)

        if method == "ramp":
            self.ramp_current(current)
        elif method == "set":
            self.set_current(current)
        else:
            raise ValueError("Unknown method for setting field, should be one of 'ramp' or 'set'.")

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
        if abs(current - self.last_current) > self.max_current_step:
            raise ValueError(f"Step in current too large: from {self.last_current} A to {current} "
                             f"A; maximum step-size is {self.max_current_step} A")

        polarity = self.current_polarity(current)
        if self.polarity_needs_changing(polarity):
            self.set_polarity(polarity)

        self.power_supply.current = abs(current)
        self.last_current = current

    @staticmethod
    def current_polarity(current):
        return int(math.copysign(1, current))

    def polarity_needs_changing(self, polarity):
        return polarity != self.polarity

    def set_polarity(self, polarity, should_stop=lambda: False):
        self.power_supply.disable()

        while not should_stop:
            if self.power_supply.measure_current == 0.:
                break
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

    def measure_field(self):
        # TODO: using the gauss-meter
        pass

    def shutdown(self):
        if self.power_supply is not None:
            self.power_supply.shutdown()
        # TODO: shutdown labjack?
        if self.gauss_meter is not None:
            self.gauss_meter.shutdown()
