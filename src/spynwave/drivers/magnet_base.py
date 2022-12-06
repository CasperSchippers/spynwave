"""
This file is part of the SpynWave package.
"""

import logging
from time import time, sleep
from abc import ABCMeta, abstractmethod

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

from spynwave.constants import config, look_for_file

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class MagnetBase(metaclass=ABCMeta):
    @property
    @abstractmethod
    def name(self):
        return "magnet_base"

    power_supply = None
    gauss_meter = None

    mirror_fields = False
    measurement_type = None

    calibration = None

    def __init__(self,
                 mirror_fields=False,
                 measurement_type=None,
                 calibration_type=None,
                 calibration_source=None):
        self.mirror_fields = mirror_fields
        self.measurement_type = measurement_type

        if calibration_type is None and "calibration" in config[self.name]:
            calibration_type = config[self.name]["calibration"]["type"]

            if calibration_source is None and "source" in config[self.name]["calibration"]:
                calibration_source = config[self.name]["calibration"]["source"]

        self.load_calibration(calibration_type, calibration_source)

    def load_calibration(self, source_type=None, source=None):
        conf = config[self.name]

        calibration = dict(
            type="interpolated lookup table",
            source_type=source_type,
            source=source,
        )

        if source_type is None:
            calibration.update(dict(
                source="system extrema",
                min_field=-conf["max field"],
                max_field=+conf["max field"],
                min_current=-conf["power-supply"]["max current"],
                max_current=+conf["power-supply"]["max current"],
                I_to_B=lambda i: (i * conf["max field"] / conf["power-supply"]["max current"]),
                B_to_I=lambda b: (b * conf["power-supply"]["max current"] / conf["max field"]),
            ))
        elif source_type == "file":
            file = look_for_file(source)
            # Load the data from file
            cal_data = pd.read_csv(file, comment="#", sep=",")

            if not ("Current (A)" in cal_data and "Field (T)" in cal_data):
                # Probably an old calibration file
                cal_data = pd.read_csv(file, header=None, delim_whitespace=True,
                                       names=["Current (A)", "Field (T)"], )

                # Ensure everything is in SI base units; should be automated/checked with the file
                cal_data["Field (T)"] *= 1e-3

            # Average multiple scans, if any
            cal_data = cal_data[["Current (A)", "Field (T)"]]\
                .groupby("Current (A)", as_index=False)\
                .mean()\
                .sort_values(by="Current (A)")\
                .reset_index(drop=True)

            i_to_b = interp1d(cal_data["Current (A)"], cal_data["Field (T)"])
            b_to_i = interp1d(cal_data["Field (T)"], cal_data["Current (A)"])

            calibration.update(dict(
                data=cal_data,
                min_field=cal_data["Field (T)"].min(),
                max_field=cal_data["Field (T)"].max(),
                min_current=cal_data["Current (A)"].min(),
                max_current=cal_data["Current (A)"].max(),
                I_to_B=i_to_b,
                B_to_I=b_to_i,
            ))

        self.calibration = calibration

    @abstractmethod
    def startup(self):
        pass

    @abstractmethod
    def shutdown(self):
        pass

    def set_field(self, field, **kwargs):
        if self.mirror_fields:
            field *= -1

        applied_field, current = self._set_field(field, **kwargs)

        if applied_field != field:
            raise ValueError(f"Applied field ({applied_field} T) differs from provided value"
                             f"({field} T).")

        return field, current

    def _set_field(self, field, **kwargs):

        current = self._field_to_current(field)
        applied_current = self._set_current(current, **kwargs)

        if applied_current != current:
            raise ValueError(f"Applied current ({applied_current} T) differs from provided value"
                             f"({current} T).")

        return field, current

    def _set_current(self, current, **kwargs):
        raise NotImplementedError("If this method is needed, it should be implemented by the"
                                  "sub-class.")
        return current

    @abstractmethod
    def measure_field(self):
        pass

    @abstractmethod
    def sweep_field(self, start, stop, ramp_rate, update_delay=0.1,
                    sleep_fn=lambda x: sleep(x), should_stop=lambda: False,
                    callback_fn=lambda x: True):
        pass

    def wait_for_stable_field(self, target=None,
                              tolerance=0.0005,
                              update_delay=0.1,
                              interval=None,
                              timeout=None,
                              sleep_fn=sleep,
                              should_stop=lambda: False):
        """ Wait for the field to stabilise. Field measurements are performed until a stable value
        is reached or the timeout has elapsed.

        :param target: Wait until the target field (in T) is (stably) reached. Default is None
        :param tolerance: The tolerance (in T) within which the field is considered stable
            (default=0.0005)
        :param update_delay: The interval between two field measurements
        :param interval: The time (in s) for which the field needs to be within tolerance to be
            considered stable.
        :param timeout: The maximum time (in s) to wait for stability
        :param sleep_fn: The sleep function to use for sleeping
        :param should_stop: A function that returns True to abort the process

        :return: The mean (stable) field, returns nan if the timed out or if aborted (should_stop)
        """
        start = time()

        number_of_fields = 2 if interval is None else int(round(interval / update_delay))

        fields = []
        while not should_stop() and not (timeout is not None and (time() - start) > timeout):
            fields.append(self.measure_field())

            # Remove first if too many datapoints
            while len(fields) > number_of_fields:
                fields.pop(0)

            # Check criteria
            local_target = target or np.mean(fields)
            within_tolerance = [abs(local_target - f) < tolerance for f in fields]
            if len(fields) == number_of_fields and all(within_tolerance):
                break

            sleep_fn(update_delay)
        else:
            # Timed out or should_stop returned True
            return np.nan

        return np.mean(fields)

    @property
    @abstractmethod
    def measurement_delay(self):
        pass

    @property
    @abstractmethod
    def field_ramp_rate(self):
        pass

    def _field_to_current(self, field):
        # Check if value within range of calibration
        if not self.calibration["min_field"] <= field <= self.calibration["max_field"]:
            raise ValueError(f"Field value ({field} T) out of bounds; should be between "
                             f"{self.calibration['min_field']} T and "
                             f"{self.calibration['max_field']} T (with the present calibration).")

        if self.calibration is not None:
            current = self.calibration["B_to_I"](field)
        else:
            raise NotImplementedError("No field calibration loaded.")

        self._check_current_within_bounds(current)

        return current

    def _current_to_field(self, current):
        # Check if value within range of calibration
        if not self.calibration["min_current"] <= current <= self.calibration["max_current"]:
            raise ValueError(f"Current value ({current} A) out of bounds; should be between "
                             f"{self.calibration['min_current']} A and "
                             f"{self.calibration['max_current']} A (with the present calibration).")
        self._check_current_within_bounds(current)

        if self.calibration is not None:
            field = self.calibration["I_to_B"](current)
        else:
            raise NotImplementedError("No field calibration loaded.")

        return field

    def _check_current_within_bounds(self, current):
        if hasattr(self, "max_current"):
            max_current = self.max_current
        else:
            max_current = self.calibration["max_current"]

        if abs(current) > max_current:
            raise ValueError(f"Current value ({current} A) out of bounds for power supply (maximum "
                             f"{max_current} A).")
