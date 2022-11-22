#
# This file is part of the PyMeasure package.
#
# Copyright (c) 2013-2022 PyMeasure Developers
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

from time import time, sleep

from pymeasure.instruments import Instrument
from pymeasure.instruments.validators import strict_discrete_set, \
    truncated_discrete_set


class LakeShore400Family(Instrument):
    """
    Represents the family of LakeShore 400 series Gaussmeters and provides a high-level interface
    for interacting with the instrument.

    """
    UNITS = ['G', 'T']
    PROBE_TYPES = {"High Sensitivity": 0,
                   "High Stability": 1,
                   "Ultra-High Sensitivity": 2}
    WRITE_DELAY = 0.05

    def __init__(self, adapter, name="Lake Shore 400 series", **kwargs):
        super().__init__(
            adapter, name,
            asrl=dict(
                baud_rate=9600,
                data_bits=7,
                stop_bits=10,
                parity=1,
                read_termination='\r',
                write_termination='\n',
            ),
            **kwargs
        )
        self.last_write_time = time()

    unit = Instrument.control(
        "UNIT?", "UNIT %s",
        """ A string property that controls the units used by the gaussmeter.
        Valid values are G (Gauss), T (Tesla). """,
        validator=strict_discrete_set,
        values=UNITS,
        dynamic=True,
    )

    probe_type = Instrument.measurement(
        "TYPE?",
        """ Returns type of field-probe used with the gaussmeter. Possible
        values are High Sensitivity, High Stability, or Ultra-High Sensitivity.
        """,
        values=PROBE_TYPES,
        map_values=True,
        dynamic=True,
    )

    auto_range = Instrument.control(
        "AUTO?", "AUTO %d",
        """ A boolean property that controls the auto-range option of the
        meter. Valid values are True and False. Note that the auto-range is
        relatively slow and might not suffice for rapid measurements.
        """,
        validator=strict_discrete_set,
        values={True: 1, False: 0},
        map_values=True,
    )

    field_range_raw = Instrument.control(
        "RANGE?", "RANGE %d",
        """ A integer property that controls the field range of the
        meter. Valid values are 0 (highest) to 3 (lowest). """,
        validator=truncated_discrete_set,
        values=range(4),
        cast=int,
        dynamic=True,
    )

    front_panel_brightness = Instrument.control(
        "BRIGT?", "BRIGT %d",
        """ An integer property that controls the brightness of the from panel
        display. Valid values are 0 (dimmest) to 7 (brightest). """,
        validator=strict_discrete_set,
        values=range(8),
        dynamic=True,
    )

    def shutdown(self):
        """ Closes the serial connection to the system. """
        self.adapter.connection.close()
        super().shutdown()

    ###################################################
    # Redefined methods to ensure time between writes #
    ###################################################

    def delay_write(self):
        if self.WRITE_DELAY is None:
            return

        while time() - self.last_write_time < self.WRITE_DELAY:
            sleep(self.WRITE_DELAY / 10)

        self.last_write_time = time()

    def write(self, command):
        self.delay_write()
        super().write(command)
