"""
This file is part of the SpynWave package.
"""

import logging


from spynwave.constants import config

from pymeasure.instruments.keithley import Keithley2400

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())


class SourceMeter:
    """ Class that represents the sourcemeter (Keithley 2400) to apply a DC excitation to the
    device under test. Can control either the current or the voltage.
    """
    name = "Source-meter"

    source_meter = None

    def __init__(self):
        self.source_meter = Keithley2400(
            config["general"]["visa-prefix"] + config[self.name]["address"],
            asrl=dict(
                baud_rate=57600,
                data_bits=8,
                stop_bits=10,
                parity=0,
                # chunk_size=1024,
                read_termination='\n',
                write_termination='\n',
            ),
        )

    def startup(self, control="Voltage"):
        # Check if enabled
        if not self.source_meter.source_enabled:
            self.source_meter.source_current = 0
            self.source_meter.source_voltage = 0
            self.source_meter.source_enabled = True

        if control.lower() == "voltage":
            self.source_meter.apply_voltage()
            self.source_meter.measure_current()
        elif control.lower() == "current":
            self.source_meter.apply_current()
            self.source_meter.measure_voltage()
        else:
            raise ValueError(f"Control mode {control} unknown; not one of 'voltage' or 'current'.")

    def ramp_to_voltage(self, voltage):
        if not self.source_meter.source_mode == "voltage":
            raise ValueError("Trying to apply voltage when the source-meter is sourcing current.")
        self.source_meter.ramp_to_voltage(voltage)

    def ramp_to_current(self, current):
        if not self.source_meter.source_mode == "current":
            raise ValueError("Trying to apply current when the source-meter is sourcing voltage.")
        self.source_meter.ramp_to_current(current)

    def measure(self):
        data = {}
        if self.source_meter.source_mode == "voltage":
            data["DC voltage (V)"] = self.source_meter.source_voltage
            data["DC current (A)"] = self.source_meter.current
        else:
            data["DC current (A)"] = self.source_meter.source_current
            data["DC voltage (V)"] = self.source_meter.voltage

        data["DC resistance (ohm)"] = data["DC voltage (V)"] / data["DC current (A)"]

        return data

    def shutdown(self, turn_off_output=True):
        if turn_off_output:
            if self.source_meter is not None:
                self.source_meter.shutdown()
