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
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())


class MixinFrequencySweep:
    # TODO: see if we can update the frequency-limits/steps/etc to the calibration?
    frequency_start = FloatParameter(
        "Start frequency",
        default=5,
        minimum=0,
        maximum=40,
        step=1,
        units="GHz",
        group_by="measurement_type",
        group_condition="Frequency sweep",
    )
    frequency_stop = FloatParameter(
        "Stop frequency",
        default=15,
        minimum=0,
        maximum=40,
        step=1,
        units="GHz",
        group_by="measurement_type",
        group_condition="Frequency sweep",
    )
    frequency_stepsize = FloatParameter(
        "Frequency step size",
        default=0.1,
        minimum=0.000404904,
        maximum=37.5,
        step=0.1,
        units="GHz",
        group_by="measurement_type",
        group_condition="Frequency sweep",
    )
    frequency_averages = IntegerParameter(
        "Number of averages (VNA)",
        default=2,
        minimum=1,
        step=1,
        group_by="measurement_type",
        group_condition="Frequency sweep",
    )

    def startup_frequency_sweep(self):
        self.vna.configure_averaging(
            enabled=True,
            average_count=self.frequency_averages,
            averaging_type=self.average_type,
        )

        self.vna.prepare_frequency_sweep(
            frequency_start=self.frequency_start * 1e9,
            frequency_stop=self.frequency_stop * 1e9,
            frequency_stepsize=self.frequency_stepsize,
        )

        log.info(f"Ramping field to {self.magnetic_field} mT")
        self.magnet.set_field(self.magnetic_field * 1e-3, controlled=True)
        log.info("Waiting for field to stabilize")
        self.magnet.wait_for_stable_field(timeout=60, should_stop=self.should_stop)

    def execute_frequency_sweep(self):
        self.vna.reset_average_count()
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
        magnet_time = abs(2 * self.magnetic_field * 1e-3 / Magnet.field_ramp_rate)

        # Based on LabVIEW estimates
        ports = 2.1 if self.measurement_ports == "2-port" else 1.
        time_per_point = 1.04 / self.rf_bandwidth

        frequency_span = self.frequency_stop - self.frequency_start
        frequency_points = int(round(frequency_span / self.frequency_stepsize))
        print(frequency_points)
        time_per_sweep = ports * time_per_point * frequency_points

        duration = self.frequency_averages * time_per_sweep
        return duration + overhead + magnet_time
