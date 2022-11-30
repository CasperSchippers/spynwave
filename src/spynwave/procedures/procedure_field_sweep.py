"""
This file is part of the SpynWave package.
"""

import logging

from pymeasure.experiment import (
    FloatParameter,
)

from spynwave.drivers import Magnet
from spynwave.procedures.threaded_sweep_base import ThreadedSweepBase
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


class MixinFieldSweep(ThreadedSweepBase):
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
    field_end = FloatParameter(
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
    @property
    def field_step(self):
        # Estimate the field step size for 2d plotting purpose
        return self.field_ramp_rate * 0.1

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
                                                   start=self.field_start * 1e-3,
                                                   stop=self.field_end * 1e-3,
                                                   ramp_rate=self.field_ramp_rate * 1e-3,
                                                   publish_data=False, )

        self.gauss_probe_thread = GaussProbeThread(self, self.magnet)
        self.vna_control_thread = VNAControlThread(self, self.vna, delay=0.001)

        if self.source_meter is not None:
            self.source_meter_thread = SourceMeterThread(self, self.source_meter, delay=0.001)

        self.threads_startup(
            data_producing_threads=[
                self.gauss_probe_thread,  # First thread is expected to be slowest in producing data
                self.vna_control_thread,
                self.source_meter_thread,
            ],
            sweep_thread=self.field_sweep_thread,
            static_data={"Frequency (Hz)": self.rf_frequency * 1e9},
            time_column="Timestamp (s)",
        )

    def execute_field_sweep(self):
        self.threads_start()

        while not self.should_stop() and not self.threads_sweep_finished():
            self.sleep(0.1)

        self.threads_stop()

        while not self.should_stop() and not self.threads_data_processed():
            self.sleep(0.1)

    def shutdown_field_sweep(self):
        self.threads_shutdown()

    def get_estimates_field_sweep(self):
        magnet = Magnet.get_magnet_class()

        overhead = 10  # Just a very poor estimate
        duration_sat = self.saturation_time + \
            abs(2 * self.saturation_field * 1e-3 / magnet.field_ramp_rate)
        duration_sweep = abs((self.field_start - self.field_end) / self.field_ramp_rate) + \
                         self.field_end * 1e-3 / magnet.field_ramp_rate
        return overhead + duration_sat + duration_sweep
