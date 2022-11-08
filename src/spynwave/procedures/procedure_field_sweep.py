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

    def startup_field_sweep(self):
        self.saturate_field()
        self.vna.prepare_field_sweep(cw_frequency=self.rf_frequency)
        self.magnet.wait_for_stable_field(timeout=60, should_stop=self.should_stop)

        # Prepare the parallel methods for the sweep

    def execute_field_sweep(self):
        # And these three methods below need to run parallel in the end
        self.parallel_field_sweep()
        self.parallel_field_measurement()
        self.parallel_cw_measurement()

        pass

    def shutdown_field_sweep(self):
        pass

    ####################
    # Helper functions #
    ####################

    def saturate_field(self):
        # Saturate the magnetic field (after saturation, go already to the starting field
        self.magnet.set_field(self.field_saturation_field)
        self.sleep(self.field_saturation_time)
        self.magnet.set_field(self.field_start)

    def parallel_field_sweep(self):
        self.magnet.sweep_field(self.field_start, self.field_stop, self.field_ramp_rate,
                                sleep_fn=self.sleep, should_stop=self.should_stop)

    def parallel_field_measurement(self, update_rate=0.1):
        while not self.should_stop():
            field = self.magnet.measure_field()

    def parallel_cw_measurement(self):
        pass


