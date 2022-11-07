"""
This file is part of the SpynWave package.
"""

import pandas as pd
from scipy.interpolate import interp1d

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

    cal_type = None
    cal_data = None

    def __init__(self):
        pass

    def startup(self):
        self.load_calibration()

    def load_calibration(self):
        # TODO: should make this less hardcoded and define standard format for table (with header)
        cal_data = pd.read_csv(calibration_file,
                               header=None,
                               names=["current", "field"],
                               delim_whitespace=True)

        # Ensure everything is in SI base units; should be automated/checked with the file
        cal_data.field *= 1e-3

        I_to_B = interp1d(cal_data.current, cal_data.field)
        B_to_I = interp1d(cal_data.field, cal_data.current)

        self.cal_type = "interpolated lookup table"
        self.cal_data = dict(
            data=cal_data,
            min_field=cal_data.field.min(),
            max_field=cal_data.field.max(),
            min_current=cal_data.current.min(),
            max_current=cal_data.current.max(),
            I_to_B=I_to_B,
            B_to_I=B_to_I,
        )

    def field_to_current(self, field):
        # Check if value within range
        if not self.cal_data["min_field"] < field < self.cal_data["max_field"]:
            raise ValueError(f"Field value ({field} T) out of bounds; should be between "
                             f"{self.cal_data['min_field']} T and {self.cal_data['max_field']} T "
                             f"(with the present calibration).")

        if self.cal_type == "interpolated lookup table":
            current = self.cal_data["B_to_I"](field)
        else:
            raise NotImplementedError(f"Current-field calibration type {self.cal_type} "
                                      f"not implemented.")

        return current

    def current_to_field(self, current):
        # Check if value within range
        if not self.cal_data["min_current"] > current > self.cal_data["max_current"]:
            raise ValueError(f"Current value ({current} A) out of bounds; should be between "
                             f"{self.cal_data['min_current']} A and {self.cal_data['max_current']} "
                             f"A (with the present calibration).")

        if self.cal_type == "interpolated lookup table":
            field = self.cal_data["I_to_B"](current)
        else:
            raise NotImplementedError(f"Current-field calibration type {self.cal_type} "
                                      f"not implemented.")

        return field

    def shutdown(self):
        pass
