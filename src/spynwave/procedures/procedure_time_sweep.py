"""
This file is part of the SpynWave package.
"""
import logging
from time import time

from pymeasure.experiment import (
    FloatParameter,
)

from spynwave.drivers import DataThread, Magnet
from spynwave.procedures.threads import (
    GaussProbeThread,
    VNAControlThread,
    SourceMeterThread,
)

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
    source_meter_thread = None

    def startup_time_sweep(self):
        log.info(f"Ramping field to {self.magnetic_field} mT")
        self.magnet.set_field(self.magnetic_field * 1e-3, controlled=True)

        self.vna.prepare_cw_sweep(cw_frequency=self.rf_frequency * 1e9, headerless=True)

        log.info("Waiting for field to stabilize")
        self.magnet.wait_for_stable_field(interval=3, timeout=60, should_stop=self.should_stop)

        # Prepare the parallel methods for the sweep
        self.gauss_probe_thread = GaussProbeThread(self, self.magnet)
        self.vna_control_thread = VNAControlThread(self, self.vna, delay=0.001)

        data_queues = [
            self.gauss_probe_thread.data_queue,
            self.vna_control_thread.data_queue,
        ]

        if self.source_meter is not None:
            self.source_meter_thread = SourceMeterThread(self, self.source_meter, delay=0.001)
            data_queues.append(self.source_meter_thread.data_queue)

        self.data_thread = DataThread(self,
                                      data_queues=data_queues,
                                      static_data={"Frequency (Hz)": self.rf_frequency * 1e9},
                                      time_column="Timestamp (s)",)

    def execute_time_sweep(self):
        self.data_thread.start()
        self.vna_control_thread.start()
        self.source_meter_thread.start()
        self.gauss_probe_thread.start()

        end_time = self.start_time + self.time_duration

        while (current_time := time()) < end_time and not self.should_stop():
            self.emit('progress', (current_time - end_time) / self.time_duration * 100)
            self.sleep(0.1)

        self.gauss_probe_thread.stop()
        self.source_meter_thread.stop()
        self.vna_control_thread.stop()
        self.data_thread.stop()

        while not self.should_stop() and not self.data_thread.all_data_processed():
            self.sleep(0.1)

    def shutdown_time_sweep(self):
        if self.gauss_probe_thread is not None:
            self.gauss_probe_thread.shutdown()

        if self.source_meter_thread is not None:
            self.source_meter_thread.shutdown()

        if self.vna_control_thread is not None:
            self.vna_control_thread.shutdown()

        if self.data_thread is not None:
            self.data_thread.shutdown()

    def get_estimates_time_sweep(self):
        magnet = Magnet.get_magnet_class()

        overhead = 10  # Just a very poor estimate
        duration_sat = abs(2 * self.magnetic_field * 1e-3 / magnet.field_ramp_rate)
        return overhead + duration_sat + self.time_duration
