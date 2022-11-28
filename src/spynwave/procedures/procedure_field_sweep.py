"""
This file is part of the SpynWave package.
"""

import logging

from pymeasure.experiment import (
    FloatParameter,
)

from spynwave.drivers import DataThread, Magnet
from spynwave.procedures.threads import (
    FieldSweepThread,
    GaussProbeThread,
    VNAControlThread,
    SourceMeterThread,
)

# Setup logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())


class MixinFieldSweep:
    # TODO: see if we can update the field-limits/etc to the setup?
    field_start = FloatParameter(
        "Start field",
        default=0.,
        # minimum=-686,
        # maximum=+686,
        step=1,
        units="mT",
        group_by="measurement_type",
        group_condition="Field sweep",
    )
    field_stop = FloatParameter(
        "Stop field",
        default=200,
        # minimum=-686,
        # maximum=+686,
        step=1,
        units="mT",
        group_by="measurement_type",
        group_condition="Field sweep",
    )
    field_ramp_rate = FloatParameter(
        "Field sweep rate",
        default=5,
        minimum=0.,
        maximum=1000.,
        step=1,
        units="mT/s",
        group_by="measurement_type",
        group_condition="Field sweep",
    )

    field_sweep_thread = None
    gauss_probe_thread = None
    vna_control_thread = None
    source_meter_thread = None

    def startup_field_sweep(self):
        self.magnet.set_field(self.field_start * 1e-3)
        self.vna.prepare_cw_sweep(cw_frequency=self.rf_frequency * 1e9, headerless=True)
        self.magnet.wait_for_stable_field(interval=3, timeout=60,
                                          sleep_fn=self.sleep,
                                          should_stop=self.should_stop)

        # Prepare the parallel methods for the sweep
        self.field_sweep_thread = FieldSweepThread(self, self.magnet,
                                                   field_start=self.field_start * 1e-3,
                                                   field_stop=self.field_stop * 1e-3,
                                                   field_ramp_rate=self.field_ramp_rate * 1e-3,
                                                   publish_data=False,)

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

    def execute_field_sweep(self):
        self.data_thread.start()
        self.vna_control_thread.start()
        self.gauss_probe_thread.start()
        self.source_meter_thread.start()
        self.field_sweep_thread.start()

        while not self.should_stop() and not self.field_sweep_thread.is_finished():
            self.sleep(0.1)

        self.field_sweep_thread.stop()
        self.source_meter_thread.stop()
        self.gauss_probe_thread.stop()
        self.vna_control_thread.stop()
        self.data_thread.stop()

        while not self.should_stop() and not self.data_thread.all_data_processed():
            self.sleep(0.1)

    def shutdown_field_sweep(self):
        if self.field_sweep_thread is not None:
            self.field_sweep_thread.shutdown()

        if self.source_meter_thread is not None:
            self.source_meter_thread.shutdown()

        if self.gauss_probe_thread is not None:
            self.gauss_probe_thread.shutdown()

        if self.vna_control_thread is not None:
            self.vna_control_thread.shutdown()

        if self.data_thread is not None:
            self.data_thread.shutdown()

    def get_estimates_field_sweep(self):
        magnet = Magnet.get_magnet_class()

        overhead = 10  # Just a very poor estimate
        duration_sat = self.saturation_time + \
            abs(2 * self.saturation_field * 1e-3 / magnet.field_ramp_rate)
        duration_sweep = abs((self.field_start - self.field_stop) / self.field_ramp_rate) + \
            self.field_stop * 1e-3 / magnet.field_ramp_rate
        return overhead + duration_sat + duration_sweep
