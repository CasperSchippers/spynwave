"""
This file is part of the SpynWave package.
"""
import logging
from time import time

from pymeasure.experiment import (
    FloatParameter,
)

from spynwave.drivers import DataThread, Magnet
from spynwave.procedures.threads import GaussProbeThread, VNAControlThread

# Setup logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())


class MixinTimeSweep:
    time_duration = FloatParameter(
        "Time sweep duration",
        default=60.,
        minimum=0,
        step=10,
        units="s",
        group_by="measurement_type",
        group_condition="Time sweep",
    )

    gauss_probe_thread = None
    vna_control_thread = None

    def startup_time_sweep(self):
        self.vna.prepare_cw_sweep(cw_frequency=self.rf_frequency * 1e9, headerless=True)

        log.info(f"Ramping field to {self.magnetic_field} mT")
        self.magnet.set_field(self.magnetic_field * 1e-3, controlled=True)
        log.info("Waiting for field to stabilize")
        self.magnet.wait_for_stable_field(timeout=60, should_stop=self.should_stop)

        # Prepare the parallel methods for the sweep
        self.gauss_probe_thread = GaussProbeThread(self, self.magnet)
        self.vna_control_thread = VNAControlThread(self, self.vna, delay=0.001)
        self.data_thread = DataThread(self, data_queues=[
            self.gauss_probe_thread.data_queue,
            self.vna_control_thread.data_queue,
        ], static_data={"Frequency (Hz)": self.rf_frequency * 1e9}, time_column="Timestamp (s)",)

    def execute_time_sweep(self):
        self.data_thread.start()
        self.vna_control_thread.start()
        self.gauss_probe_thread.start()

        end_time = self.start_time + self.time_duration

        while (current_time := time()) < end_time and not self.should_stop():
            self.emit('progress', (current_time - end_time) / self.time_duration * 100)
            self.sleep(0.1)

        self.gauss_probe_thread.stop()
        self.vna_control_thread.stop()
        self.data_thread.stop()

        while not self.should_stop() and not self.data_thread.all_data_processed():
            self.sleep(0.1)

    def shutdown_time_sweep(self):
        if self.gauss_probe_thread is not None and self.gauss_probe_thread.is_alive():
            try:
                self.gauss_probe_thread.join(2)
            except RuntimeError as exc:
                log.error(exc)

        if self.vna_control_thread is not None and self.vna_control_thread.is_alive():
            try:
                self.vna_control_thread.join(2)
            except RuntimeError as exc:
                log.error(exc)

        if self.data_thread is not None and self.data_thread.is_alive():
            try:
                self.data_thread.join(5)
            except RuntimeError as exc:
                log.error(exc)

    ####################
    # Helper functions #
    ####################

    def get_estimates_time_sweep(self):
        magnet = Magnet.get_magnet_class()

        overhead = 10  # Just a very poor estimate
        duration_sat = abs(2 * self.magnetic_field * 1e-3 / magnet.field_ramp_rate)
        return overhead + duration_sat + self.time_duration
