"""
This file is part of the SpynWave package.
"""
from time import time, sleep

from pymeasure.experiment import (
    Procedure, Parameter, FloatParameter, BooleanParameter,
    IntegerParameter, ListParameter, Metadata
)


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
    field_mirrored = BooleanParameter(
        "Include mirrored fields",
        default=False,
        group_by="measurement_type",
        group_condition="Field sweep",
    )
    field_saturation = FloatParameter(
        "Stop field",
        default=0.2,
        minimum=-0.660,
        maximum=+0.660,
        units="T",
        group_by="measurement_type",
        group_condition="Field sweep",
    )

    def startup_field_sweep(self):
        pass

    def execute_field_sweep(self):
        pass

    def shutdown_field_sweep(self):
        pass

