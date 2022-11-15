"""
This file is part of the SpynWave package.
"""

import os
import logging
import ctypes
from copy import deepcopy

from pyvisa import VisaIOError
from pyvisa.constants import VI_ERROR_TMO

from pymeasure.display.Qt import QtWidgets
from pymeasure.display.windows import ManagedWindow

from pymeasure.experiment import Results, unique_filename

from spynwave.procedure import PSWSProcedure
from spynwave.drivers import VNA
from spynwave.widgets import SpinWaveSequencerWidget
from spynwave.pymeasure_patches.pandas_formatter import CSVFormatterPandas


# Setup logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

# Register as separate software
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("fna.MeasurementSoftware.SpynWave")


class Window(ManagedWindow):
    # TODO: this also needs an more complicated sequencer, maybe as a tabwidget??
    #  Or see if I can make tabs for the input-widget
    def __init__(self):
        super().__init__(
            procedure_class=PSWSProcedure,
            inputs=(
                "AB_filename_base",
                "measurement_type",
                "rf_frequency",
                "magnetic_field",
                "frequency_start",
                "frequency_stop",
                "frequency_points",
                "field_start",
                "field_stop",
                "field_ramp_rate",
                "field_include_mirrored",
                "field_saturation_field",
                "frequency_averages",
                "rf_advanced_settings",
                "average_type",
                "measurement_ports",
                "rf_power",
                "rf_bandwidth",
            ),
            x_axis="Field (T)",
            y_axis="S11 real",
            displays=(
                "measurement_type",
                "frequency_averages",
            ),
            sequencer=False,
            inputs_in_scrollarea=True,
            directory_input=True,
        )

        self.update_inputs_from_VNA()

        self.directory_line.setText(os.getcwd())

    def queue(self, *args, procedure=None):
        if procedure is None:
            procedure = self.make_procedure()

        folder = self.directory
        filename = procedure.AB_filename_base
        measurement_type = procedure.measurement_type

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

        # Can be changed when the CSVFormatterPandas is merged
        results.formatter = CSVFormatterPandas(
            columns=results.procedure.DATA_COLUMNS,
            delimiter=results.DELIMITER,
            line_break=results.LINE_BREAK
            )

        experiment = self.new_experiment(results)
        self.manager.queue(experiment)

        # Adjust graph depending on the measurement type
        if measurement_type == "Frequency sweep":
            self.plot_widget.columns_x.setCurrentText("Frequency (Hz)")
            self.plot_widget.plot_frame.change_x_axis("Frequency (Hz)")
        elif measurement_type == "Field sweep":
            self.plot_widget.columns_x.setCurrentText("Field (T)")
            self.plot_widget.plot_frame.change_x_axis("Field (T)")

    def queue_repeated(self, *args, procedure=None):
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
                # "average_nr": i + 1,
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

    def _setup_ui(self):
        """ Re-implementation of the _setup_ui method to include the customized sequencer widget
        """
        if use_sequencer := self.use_sequencer:
            self.sequencer = SpinWaveSequencerWidget(parent=self)

        # Temporarily disable the use-sequencer, such that no new sequencer-widget is instantiated
        self.use_sequencer = False
        super()._setup_ui()
        self.use_sequencer = use_sequencer

    def update_inputs_from_VNA(self):
        """ Inquire values for the frequency range and bandwidth from the VNA and set them as new
        default values in the interface. """

        try:
            with VNA.connect_vectorstar() as vectorstar:

                # First get current state, such that it can be returned to afterwards
                cw_mode_enabled = vectorstar.ch_1.cw_mode_enabled
                frequency_CW = vectorstar.ch_1.frequency_CW
                number_of_points = vectorstar.ch_1.number_of_points
                frequency_start = vectorstar.ch_1.frequency_start
                frequency_stop = vectorstar.ch_1.frequency_stop

                # Set widest possible range
                vectorstar.ch_1.cw_mode_enabled = False
                vectorstar.ch_1.frequency_start = vectorstar.ch_1.FREQUENCY_RANGE[0]
                vectorstar.ch_1.frequency_stop = vectorstar.ch_1.FREQUENCY_RANGE[1]
                vectorstar.ch_1.number_of_points = 100000

                # Get the values that are within the calibration
                frequency_min = vectorstar.ch_1.frequency_start
                frequency_max = vectorstar.ch_1.frequency_stop
                frequency_steps = vectorstar.ch_1.number_of_points
                bandwidth = vectorstar.ch_1.bandwidth
                power_level = vectorstar.ch_1.pt_1.power_level

                # Return to the original values
                vectorstar.ch_1.cw_mode_enabled = cw_mode_enabled
                vectorstar.ch_1.frequency_CW = frequency_CW
                vectorstar.ch_1.number_of_points = number_of_points
                vectorstar.ch_1.frequency_start = frequency_start
                vectorstar.ch_1.frequency_stop = frequency_stop

                vectorstar.return_to_local()
        except VisaIOError as exc:
            if not exc.error_code == VI_ERROR_TMO:
                raise exc
            log.warning("Could not retrieve limits from VNA: timed out.")
            return

        self.inputs.frequency_start.setMinimum(frequency_min)
        self.inputs.frequency_start.setMaximum(frequency_max)
        self.inputs.frequency_start.setValue(frequency_min)

        self.inputs.frequency_stop.setMinimum(frequency_min)
        self.inputs.frequency_stop.setMaximum(frequency_max)
        self.inputs.frequency_stop.setValue(frequency_max)

        self.inputs.frequency_points.setMaximum(frequency_steps)
        self.inputs.frequency_points.setValue(frequency_steps)

        self.inputs.rf_frequency.setMinimum(frequency_min)
        self.inputs.rf_frequency.setMaximum(frequency_max)
        self.inputs.rf_frequency.setValue(frequency_CW)

        self.inputs.rf_bandwidth.setValue(bandwidth)
        self.inputs.rf_power.setValue(power_level)
