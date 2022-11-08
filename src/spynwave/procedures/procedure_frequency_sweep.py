"""
This file is part of the SpynWave package.
"""
import logging
from time import time, sleep

from pymeasure.experiment import (
    Procedure, Parameter, FloatParameter, BooleanParameter,
    IntegerParameter, ListParameter, Metadata
)

# Setup logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class MixinFrequencySweep:
    # TODO: see if we can update the frequency-limits/steps/etc to the calibration?
    frequency_start = FloatParameter(
        "Start frequency",
        default=5e9,
        minimum=0,
        maximum=40e9,
        units="Hz",
        group_by="measurement_type",
        group_condition="Frequency sweep",
    )
    frequency_stop = FloatParameter(
        "Stop frequency",
        default=15e9,
        minimum=0,
        maximum=40e9,
        units="Hz",
        group_by="measurement_type",
        group_condition="Frequency sweep",
    )
    frequency_points = IntegerParameter(
        "Frequency points",
        default=201,
        minimum=1,
        maximum=100000,
        group_by="measurement_type",
        group_condition="Frequency sweep",
    )

    def startup_frequency_sweep(self):
        self.vna.prepare_frequency_sweep(
            frequency_start=self.frequency_start,
            frequency_stop=self.frequency_stop,
            frequency_points=self.frequency_points,
        )
        log.info(f"Ramping field to {self.magnetic_field} T")
        self.magnet.set_field(self.magnetic_field, controlled=True)
        log.info(f"Waiting for field to stabilize")
        self.magnet.wait_for_stable_field(timeout=60, should_stop=self.should_stop)

    def execute_frequency_sweep(self):
        self.vna.trigger_frequency_sweep()
        start = time()

        field_points = [self.magnet.measure_field()]

        while not self.should_stop():
            cnt = self.vna.ch_1.average_sweep_count
            self.emit("progress", cnt/self.averages * 100)

            # Measure the field while waiting
            field_points.append(self.magnet.measure_field())

            if cnt >= self.averages:
                break
            self.sleep()

        stop = time()

        data = self.vna.grab_data()

        data["Timestamp (s)"] = (stop + start) / 2
        data["Field (T)"] = sum(field_points) / len(field_points)

        self.emit("results", data)

    def shutdown_frequency_sweep(self):
        pass
