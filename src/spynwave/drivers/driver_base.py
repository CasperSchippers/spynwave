"""
This file is part of the SpynWave package.
"""

import logging
from time import sleep, time
import math

import numpy as np

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())


class DriverBase:
    def sweep(self, start, stop, ramp_rate, set_fn, update_delay=0.1,
              sleep_fn=lambda x: sleep(x), should_stop=lambda: False,
              callback_fn=lambda x: None, **kwargs):

        sweep_duration = abs((start - stop) / ramp_rate)
        number_of_updates = math.ceil(sweep_duration / update_delay)
        value_list = np.linspace(start, stop, number_of_updates + 1)

        t0 = 0
        for value in value_list:
            if (delay := update_delay + (t0 - time())) > 0:
                sleep_fn(delay)
            else:
                log.debug(f"Setting next value in sweep took {-delay} longer than update delay "
                          f"({update_delay - delay}s vs {update_delay} s")
            t0 = time()

            set_fn(value, **kwargs)
            callback_fn(value)
            if should_stop():
                break
