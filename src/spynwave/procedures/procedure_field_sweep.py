"""
This file is part of the SpynWave package.
"""

import logging

from pymeasure.experiment import (
    FloatParameter, BooleanParameter,
)

from spynwave.drivers import DataThread, Magnet
from spynwave.procedures.threads import FieldSweepThread, GaussProbeThread, VNAControlThread

# Setup logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class MixinFieldSweep:
    # TODO: see if we can update the field-limits/etc to the setup?
    field_start = FloatParameter(
        "Start field",
        default=0.,
        minimum=-0.660,
        maximum=+0.660,
        units="T",
        group_by="measurement_type",
        group_condition="Field sweep",
    )
    field_stop = FloatParameter(
        "Stop field",
        default=0.2,
        minimum=-0.660,
        maximum=+0.660,
        units="T",
        group_by="measurement_type",
        group_condition="Field sweep",
    )
    field_ramp_rate = FloatParameter(
        "Field sweep rate",
        default=0.005,
        minimum=0.,
        maximum=1.,
        units="T/s",
        group_by="measurement_type",
        group_condition="Field sweep",
    )
    # TODO: implement mirrored fields to generate a second measurement
    field_include_mirrored = BooleanParameter(
        "Include mirrored fields",
        default=False,
        group_by="measurement_type",
        group_condition="Field sweep",
    )
    field_saturation_field = FloatParameter(
        "Saturation field",
        default=0.2,
        minimum=-0.660,
        maximum=+0.660,
        units="T",
        group_by="measurement_type",
        group_condition="Field sweep",
    )
    field_saturation_time = FloatParameter(
        "Saturation ",
        default=2,
        minimum=0,
        maximum=120,
        units="s",
        group_by="measurement_type",
        group_condition="Field sweep",
    )

    field_sweep_thread = None
    gauss_probe_thread = None
    vna_control_thread = None

    def startup_field_sweep(self):
        self.saturate_field()
        self.vna.prepare_cw_sweep(cw_frequency=self.rf_frequency, headerless=True)
        self.magnet.wait_for_stable_field(timeout=60, should_stop=self.should_stop)

        # Prepare the parallel methods for the sweep
        self.field_sweep_thread = FieldSweepThread(self, self.magnet,
                                                   field_start=self.field_start,
                                                   field_stop=self.field_stop,
                                                   field_ramp_rate=self.field_ramp_rate,
                                                   publish_data=False,)
        self.gauss_probe_thread = GaussProbeThread(self, self.magnet)
        self.vna_control_thread = VNAControlThread(self, self.vna, delay=0.001)
        self.data_thread = DataThread(self, data_queues=[
            self.gauss_probe_thread.data_queue,
            self.vna_control_thread.data_queue,
        ], static_data={"Frequency (Hz)": self.rf_frequency}, time_column="Timestamp (s)",)

    def execute_field_sweep(self):
        self.data_thread.start()
        self.field_sweep_thread.start()
        self.gauss_probe_thread.start()
        self.vna_control_thread.start()

        while not self.should_stop() and not self.field_sweep_thread.is_finished():
            self.sleep(0.1)

        self.field_sweep_thread.stop()
        self.gauss_probe_thread.stop()
        self.vna_control_thread.stop()
        self.data_thread.stop()

        while not self.should_stop() and not self.data_thread.all_data_processed():
            self.sleep(0.1)

    def shutdown_field_sweep(self):
        if self.field_sweep_thread is not None and self.field_sweep_thread.is_alive():
            try:
                self.field_sweep_thread.join(2)
            except RuntimeError as exc:
                log.error(exc)

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

    def saturate_field(self):
        # Saturate the magnetic field (after saturation, go already to the starting field
        self.magnet.set_field(self.field_saturation_field)
        self.sleep(self.field_saturation_time)
        self.magnet.set_field(self.field_start)

    def get_estimates_field_sweep(self):
        overhead = 10  # Just a very poor estimate
        duration_sat = self.field_saturation_time + \
            abs(2 * self.field_saturation_field / Magnet.current_ramp_rate)
        duration_sweep = abs((self.field_start - self.field_stop) / self.field_ramp_rate) + \
            self.field_stop / Magnet.current_ramp_rate
        return overhead + duration_sat + duration_sweep
