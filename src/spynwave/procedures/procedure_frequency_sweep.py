"""
This file is part of the SpynWave package.
"""

import logging
from time import time

from pymeasure.experiment import (
    FloatParameter, IntegerParameter
)

from spynwave.drivers import Magnet

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
    frequency_averages = IntegerParameter(
        "Number of averages (VNA)",
        default=2,
        minimum=1,
        group_by="measurement_type",
        group_condition="Frequency sweep",
    )

    def startup_frequency_sweep(self):
        self.magnet.gauss_meter_set_fast_mode(False)

        self.vna.configure_averaging(
            enabled=True,
            average_count=self.frequency_averages,
            averaging_type=self.average_type,
        )

        self.vna.prepare_frequency_sweep(
            frequency_start=self.frequency_start,
            frequency_stop=self.frequency_stop,
            frequency_points=self.frequency_points,
        )

        log.info(f"Ramping field to {self.magnetic_field} T")
        self.magnet.set_field(self.magnetic_field, controlled=True)
        log.info("Waiting for field to stabilize")
        self.magnet.wait_for_stable_field(timeout=60, should_stop=self.should_stop)

    def execute_frequency_sweep(self):
        self.vna.trigger_measurement()
        start = time()

        field_points = [self.magnet.measure_field()]

        while not self.should_stop():
            cnt = self.vna.averages_done()
            self.emit("progress", cnt/self.frequency_averages * 100)

            # Measure the field while waiting
            field_points.append(self.magnet.measure_field())

            if cnt >= self.frequency_averages:
                break
            self.sleep()

        stop = time()

        data = self.vna.grab_data(CW_mode=False)

        data["Timestamp (s)"] = (stop + start) / 2
        data["Field (T)"] = sum(field_points) / len(field_points)

        self.emit("results", data)

    def shutdown_frequency_sweep(self):
        pass

    def get_estimates_frequency_sweep(self):
        overhead = 10  # Just a very poor estimate
        magnet_time = abs(2 * self.magnetic_field / Magnet.current_ramp_rate)

        # Based on LabVIEW estimates
        ports = 2.1 if self.measurement_ports == "2-port" else 1.
        time_per_point = 1.04 / self.rf_bandwidth
        time_per_sweep = ports * time_per_point * self.frequency_points

        duration = self.frequency_averages * time_per_sweep
        return duration + overhead + magnet_time
