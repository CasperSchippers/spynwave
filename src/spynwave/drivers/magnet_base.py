"""
This file is part of the SpynWave package.
"""

import logging
from time import time, sleep
from abc import ABCMeta, abstractmethod

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class MagnetBase(metaclass=ABCMeta):
    power_supply = None
    gauss_meter = None

    mirror_fields = False
    measurement_type = None

    def __init__(self, mirror_fields=False, measurement_type=None):
        self.mirror_fields = mirror_fields
        self.measurement_type = measurement_type

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

    def wait_for_stable_field(self, tolerance=0.00025, timeout=None, should_stop=lambda: False):
        start = time()
        field = self.measure_field()
        while not should_stop() and not (timeout is not None and (time() - start) > timeout):
            if abs(field - (field := self.measure_field())) < tolerance:
                break

    @property
    @abstractmethod
    def measurement_delay(self):
        pass

    @property
    @abstractmethod
    def field_ramp_rate(self):
        pass
