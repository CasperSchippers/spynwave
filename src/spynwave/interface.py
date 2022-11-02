import os
import logging
import ctypes

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
            ),
            x_axis="Field (T)",
            y_axis="S11 real",
            displays=(
            ),
            sequencer=True,
            inputs_in_scrollarea=True,
            directory_input=True,
        )

        self.directory_line.setText(os.getcwd())

    def queue(self, *args, procedure=None):

        if procedure is None:
            procedure = self.make_procedure()

        folder = self.directory
        procedure.set_parameters({
            "AA_folder": folder
        })

        filename = procedure.AB_filename_base

        if replace_placeholders is not None:
            filename = replace_placeholders(filename, procedure)

        filename = unique_filename(
            folder,
            prefix=filename,
            ext="txt",
            datetimeformat="",
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
