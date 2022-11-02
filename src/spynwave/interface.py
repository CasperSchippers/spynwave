"""
This file is part of the SpynWave package.
"""

import os
import logging
import ctypes
from copy import deepcopy

from pymeasure.display.Qt import QtWidgets
from pymeasure.display.windows import ManagedWindow
from pymeasure.experiment import Results, unique_filename, replace_placeholders

from spynwave.procedure import PSWSProcedure


# Setup logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

# Register as separate software
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("fna.MeasurementSoftware.SpynWave")


class Window(ManagedWindow):
    def __init__(self):
        super().__init__(
            procedure_class=PSWSProcedure,
            inputs=(
                "AB_filename_base",
                "measurement_type",
                "averages",
                "rf_frequency",
                "magnetic_field",
                "rf_power",
                "rf_bandwidth",
            ),
            x_axis="Field (T)",
            y_axis="S11 real",
            displays=(
                "measurement_type",
                "average_nr",
            ),
            sequencer=True,
            inputs_in_scrollarea=True,
            directory_input=True,
        )

        self.directory_line.setText(os.getcwd())

    def queue(self, *args, procedure=None):
        if procedure is None:
            main_procedure = self.make_procedure()
        else:
            main_procedure = procedure

        folder = self.directory
        filename_base = main_procedure.AB_filename_base

        # Queue a series of averages
        for i in range(main_procedure.averages):
            QtWidgets.QApplication.processEvents()
            procedure = deepcopy(main_procedure)

            procedure.set_parameters({
                "AA_folder": folder,
                "average_nr": i + 1,
            })

            filename = unique_filename(
                folder,
                prefix=filename_base,
                ext="txt",
                datetimeformat="",
                procedure=procedure
            )

            results = Results(procedure, filename)
            experiment = self.new_experiment(results)
            self.manager.queue(experiment)

    def new_curve(self, *args, **kwargs):
        curve = super().new_curve(*args, **kwargs, connect="finite")
        if curve is not None:
            curve.setSymbol("o")
            curve.setSymbolPen(curve.pen)
        return curve
