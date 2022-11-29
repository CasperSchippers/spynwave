"""
This file is part of the SpynWave package.
"""

import logging

from pymeasure.experiment import (
    FloatParameter,
)

from spynwave.procedures.threaded_sweep_base import ThreadedSweepBase
from spynwave.procedures.threads import (
    GaussProbeThread,
    VNAControlThread,
    SourceMeterThread,
)

# Setup logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())


class MixinDCSweep(ThreadedSweepBase):
    dc_voltage_start = FloatParameter(
        "Start voltage",
        default=0.,
        minimum=-200.,
        maximum=+200.,
        step=1.,
        units="V",
        group_by=["measurement_type", "dc_regulate"],
        group_condition=["DC sweep", "Voltage"],
    )
    dc_voltage_stop = FloatParameter(
        "Stop voltage",
        default=10.,
        minimum=-200.,
        maximum=+200.,
        step=1.,
        units="V",
        group_by=["measurement_type", "dc_regulate"],
        group_condition=["DC sweep", "Voltage"],
    )
    dc_voltage_rate = FloatParameter(
        "Voltage sweep rate",
        default=0.1,
        step=0.1,
        units="V/s",
        group_by=["measurement_type", "dc_regulate"],
        group_condition=["DC sweep", "Voltage"],
    )

    dc_current_start = FloatParameter(
        "Start current",
        default=0.,
        minimum=-1000.,
        maximum=+1000.,
        step=1.,
        units="mA",
        group_by=["measurement_type", "dc_regulate"],
        group_condition=["DC sweep", "Current"],
    )
    dc_current_stop = FloatParameter(
        "Stop current",
        default=10.,
        minimum=-1000.,
        maximum=+1000.,
        step=1.,
        units="mA",
        group_by=["measurement_type", "dc_regulate"],
        group_condition=["DC sweep", "Current"],
    )
    dc_current_rate = FloatParameter(
        "Current sweep rate",
        default=10.,
        step=1.,
        units="mA/s",
        group_by=["measurement_type", "dc_regulate"],
        group_condition=["DC sweep", "Current"],
    )

    dc_sweep_thread = None
    gauss_probe_thread = None
    vna_control_thread = None
    source_meter_thread = None

    def startup_dc_sweep(self):
        self.magnet.set_field(self.field_start * 1e-3)
        self.vna.prepare_cw_sweep(cw_frequency=self.rf_frequency * 1e9, headerless=True)
        self.magnet.wait_for_stable_field(interval=3, timeout=60,
                                          sleep_fn=self.sleep,
                                          should_stop=self.should_stop)

        # Prepare the parallel methods for the sweep
        self.dc_sweep_thread

        self.gauss_probe_thread = GaussProbeThread(self, self.magnet)
        self.vna_control_thread = VNAControlThread(self, self.vna, delay=0.001)

        self.source_meter_thread = SourceMeterThread(self, self.source_meter, delay=0.001)

        self.threads_startup(
            data_producing_threads=[
                self.gauss_probe_thread,  # First thread is expected to be slowest in producing data
                self.vna_control_thread,
                self.source_meter_thread,
            ],
            sweep_thread=self.dc_sweep_thread,
            static_data={"Frequency (Hz)": self.rf_frequency * 1e9},
            time_column="Timestamp (s)",
        )

    def execute_dc_sweep(self):
        self.threads_start()

        while not self.should_stop() and not self.threads_sweep_finished():
            self.sleep(0.1)

        self.threads_stop()

        while not self.should_stop() and not self.threads_data_processed():
            self.sleep(0.1)

    def shutdown_dc_sweep(self):
        self.threads_shutdown()

    def get_estimates_dc_sweep(self):
        return 0
        # magnet = Magnet.get_magnet_class()
        #
        # overhead = 10  # Just a very poor estimate
        # duration_sat = self.saturation_time + \
        #     abs(2 * self.saturation_field * 1e-3 / magnet.field_ramp_rate)
        # duration_sweep = abs((self.field_start - self.field_stop) / self.field_ramp_rate) + \
        #     self.field_stop * 1e-3 / magnet.field_ramp_rate
        # return overhead + duration_sat + duration_sweep