"""
This file is part of the SpynWave package.
"""

import logging

from pymeasure.experiment import Results, unique_filename

from spynwave.widgets import SpynWaveWindowBase
from spynwave.magnet_calibration.procedure import MagnetCalibrationProcedure


# Setup logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())


class MagnetCalibrationWindow(SpynWaveWindowBase):
    def __init__(self):
        super().__init__(
            procedure_class=MagnetCalibrationProcedure,
            inputs=(
                "max_current",
                "symmetric_currents",
                "min_current",
                "current_steps",
                "dwell_time",
                "number_of_sweeps",
                "field_scaling_factor",
            ),
            x_axis="Current (A)",
            y_axis="Field (T)",
            displays=(
                "min_current",
                "max_current",
                "symmetric_currents",
            ),
        )

    def queue(self, procedure=None):
        if procedure is None:
            procedure = self.make_procedure()

        folder = self.directory
        filename = self.filename

        if procedure.symmetric_currents:
            procedure.min_current = -procedure.max_current

        procedure.set_parameters({
            "AA_folder": folder,
        })

        filename = unique_filename(
            folder,
            prefix=filename,
            ext="txt",
            datetimeformat="",
            procedure=procedure
        )

        results = Results(procedure, filename)
        experiment = self.new_experiment(results)
        self.manager.queue(experiment)
