"""
This file is part of the SpynWave package.
"""

import logging
from time import time, sleep
from abc import ABCMeta, abstractmethod

import numpy as np

from spynwave.constants import config

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

    cal_type = None
    cal_data = None

    def __init__(self,
                 mirror_fields=False,
                 measurement_type=None,
                 calibration_type="linear interpolated"):
        self.mirror_fields = mirror_fields
        self.measurement_type = measurement_type

        if calibration_type is not None:
            self.load_calibration(calibration_type)

    def load_calibration(self, calibration_type):
        self.cal_type = calibration_type
        conf = config[self.name]
        if self.cal_type == "linear interpolated":
            self.cal_data = dict(
                data=None,
                min_field=-conf["max field"],
                max_field=+conf["max field"],
                min_current=-conf["power-supply"]["max current"],
                max_current=+conf["power-supply"]["max current"],
                I_to_B=lambda I: (I * conf["max field"] / conf["power-supply"]["max current"]),
                B_to_I=lambda B: (B * conf["power-supply"]["max current"] / conf["max field"]),
            )

    @abstractmethod
    def startup(self):
        pass

    @abstractmethod
    def shutdown(self):
        pass

    def set_field(self, field, *args, **kwargs):
        if self.mirror_fields:
            field *= -1

        applied_field = self._set_field(field, *args, **kwargs)

        if applied_field != field:
            raise ValueError(f"Applied field ({applied_field} T) differs from provided value"
                             f"({field} T).")

        return field

    @abstractmethod
    def _set_field(self, field):
        pass

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
        if not self.cal_data["min_field"] <= field <= self.cal_data["max_field"]:
            raise ValueError(f"Field value ({field} T) out of bounds; should be between "
                             f"{self.cal_data['min_field']} T and {self.cal_data['max_field']} T "
                             f"(with the present calibration).")

        if self.cal_type is not None:
            current = self.cal_data["B_to_I"](field)
        else:
            raise NotImplementedError(f"Current-field calibration type {self.cal_type} "
                                      f"not implemented.")

        self._check_current_within_bounds(current)

        return current

    def _current_to_field(self, current):
        # Check if value within range of calibration
        if not self.cal_data["min_current"] <= current <= self.cal_data["max_current"]:
            raise ValueError(f"Current value ({current} A) out of bounds; should be between "
                             f"{self.cal_data['min_current']} A and {self.cal_data['max_current']} "
                             f"A (with the present calibration).")
        self._check_current_within_bounds(current)

        if self.cal_type is not None:
            field = self.cal_data["I_to_B"](current)
        else:
            raise NotImplementedError(f"Current-field calibration type {self.cal_type} "
                                      f"not implemented.")

        return field

    def _check_current_within_bounds(self, current):
        if hasattr(self, "max_current"):
            max_current = self.max_current
        else:
            max_current = self.cal_data["max_current"]

        if abs(current) > max_current:
            raise ValueError(f"Current value ({current} A) out of bounds for power supply (maximum "
                             f"{max_current} A).")
