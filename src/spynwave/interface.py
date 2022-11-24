"""
This file is part of the SpynWave package.
"""

import os
import logging

from pyvisa import VisaIOError
from pyvisa.constants import VI_ERROR_TMO

from pymeasure.display.Qt import QtWidgets, QtCore, QtGui
from pymeasure.display.windows import ManagedWindow

from pymeasure.experiment import Results, unique_filename

from spynwave.procedure import PSWSProcedure
from spynwave.drivers import VNA
from spynwave.widgets import SpinWaveSequencerWidget
from spynwave.pymeasure_patches.pandas_formatter import CSVFormatterPandas


# Setup logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())


class PSWSWindow(ManagedWindow):
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
                "frequency_stepsize",
                "field_start",
                "field_stop",
                "field_ramp_rate",
                "field_saturation_field",
                "time_duration",
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
                "mirrored_field",
                "frequency_averages",
            ),
            sequencer=True,
            inputs_in_scrollarea=True,
            directory_input=True,
        )

        self._setup_log_widget()

        # self.update_inputs_from_vna()

        self.directory_line.setText(os.getcwd())

        self.resize(1200, 900)

    def queue(self, procedure=None):
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

    def new_curve(self, *args, **kwargs):
        curve = super().new_curve(*args, **kwargs, connect="finite")
        if curve is not None:
            curve.setSymbol("o")
            curve.setSymbolPen(curve.pen)
        return curve

    #################################################################
    # Methods below extend the ManagedWindow with custom components #
    #################################################################

    def _setup_ui(self):
        """ Re-implementation of the _setup_ui method to include the customized sequencer widget
        """
        if use_sequencer := self.use_sequencer:
            self.sequencer = SpinWaveSequencerWidget(parent=self)

        # Temporarily disable the use-sequencer, such that no new sequencer-widget is instantiated
        self.use_sequencer = False
        super()._setup_ui()
        self.use_sequencer = use_sequencer

        # Link the measurement-type drop-box to the visible pane
        if self.use_sequencer:
            self.inputs.measurement_type.currentTextChanged.connect(self.sequencer.set_pane_focus)
            self.sequencer.set_pane_focus(self.inputs.measurement_type.currentText())

        # remove margin
        self.inputs.layout().setContentsMargins(0, 0, 0, 0)

    def update_inputs_from_vna(self):
        """ Inquire values for the frequency range and bandwidth from the VNA and set them as new
        default values in the interface. """
        # TODO: see if this can be made asynchronous

        try:
            with VNA.connect_vectorstar() as vectorstar:

                # First get current state, such that it can be returned to afterwards
                cw_mode_enabled = vectorstar.ch_1.cw_mode_enabled
                frequency_cw = vectorstar.ch_1.frequency_CW
                number_of_points = vectorstar.ch_1.number_of_points
                frequency_start = vectorstar.ch_1.frequency_start
                frequency_stop = vectorstar.ch_1.frequency_stop

                # Set widest possible range
                vectorstar.ch_1.cw_mode_enabled = False
                vectorstar.ch_1.frequency_start = vectorstar.ch_1.FREQUENCY_RANGE[0]
                vectorstar.ch_1.frequency_stop = vectorstar.ch_1.FREQUENCY_RANGE[1]
                vectorstar.ch_1.number_of_points = 100000

                # Get the values that are within the calibration
                frequency_min = vectorstar.ch_1.frequency_start * 1e-9
                frequency_max = vectorstar.ch_1.frequency_stop * 1e-9
                frequency_steps = vectorstar.ch_1.number_of_points
                bandwidth = vectorstar.ch_1.bandwidth
                power_level = vectorstar.ch_1.pt_1.power_level

                # Return to the original values
                vectorstar.ch_1.cw_mode_enabled = cw_mode_enabled
                vectorstar.ch_1.frequency_CW = frequency_cw
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

        # self.inputs.frequency_stepsize.setMaximum(frequency_steps)
        stepsize = (frequency_max - frequency_min) / frequency_steps
        self.inputs.frequency_stepsize.setValue(stepsize)
        self.inputs.frequency_stepsize.setSingleStep(stepsize)

        self.inputs.rf_frequency.setMinimum(frequency_min)
        self.inputs.rf_frequency.setMaximum(frequency_max)
        self.inputs.rf_frequency.setValue(frequency_cw)

        self.inputs.rf_bandwidth.setValue(bandwidth)
        self.inputs.rf_power.setValue(power_level)

    def _setup_log_widget(self):
        """ Adjust the log-widget.
        Sets the logging level to INFO, adds blinking functionality and color-coding for warning-
        and error-messages.

        """
        self.log_widget.handler.setLevel(logging.INFO)

        self._blink_qtimer = QtCore.QTimer()
        self._blink_color = None
        self._blink_state = False

        self.tabs.tabBar().setIconSize(QtCore.QSize(12, 12))

        # Connect a bunch of slots
        # For the blinking
        self._blink_qtimer.timeout.connect(self._blink)
        # For stopping the blinking
        self.tabs.tabBar().currentChanged.connect(self._blink_stop)
        # For starting the blinking
        self.log_widget.handler.connect(self._blink_log_widget)

        # Replace the message-handler to color error and warning lines
        self.log_widget.handler.connect(self._append_to_log)
        self.log_widget.handler.emitter.record.disconnect(self.log_widget.view.appendPlainText)

    def _append_to_log(self, message):
        if not ("(ERROR)" in message or "(WARNING)" in message):
            return self.log_widget.view.appendPlainText(message)

        color = "Red" if "(ERROR)" in message else "DarkOrange"

        html_message = f"<font color=\"{color}\">{message}</font>"\
            .replace("\r\n", "<br>  ")\
            .replace("\n", "<br>  ")\
            .replace("\r", "<br>  ")\
            .replace("  ", "&nbsp;&nbsp;")\
            .replace("\t", "&nbsp;&nbsp;&nbsp;&nbsp;")

        return self.log_widget.view.appendHtml(html_message)

    def _blink(self):
        if self._blink_state:
            self.tabs.tabBar().setTabTextColor(
                self.tabs.indexOf(self.log_widget),
                QtGui.QColor("black")
            )
        else:
            self.tabs.tabBar().setTabTextColor(
                self.tabs.indexOf(self.log_widget),
                QtGui.QColor(self._blink_color)
            )

        self._blink_state = not self._blink_state

    def _blink_stop(self, index):
        if index == self.tabs.indexOf(self.log_widget):
            self._blink_qtimer.stop()
            self._blink_state = True
            self._blink()

            self._blink_color = None
            self.tabs.setTabIcon(self.tabs.indexOf(self.log_widget), QtGui.QIcon())

    def _blink_log_widget(self, message: str):
        if not ("(ERROR)" in message or "(WARNING)" in message):
            return

        # Check if the current tab is actually the log-tab
        if self.tabs.currentIndex() == self.tabs.indexOf(self.log_widget):
            self._blink_stop(self.tabs.currentIndex())
            return

        # Define color and icon based on severity
        # If already red, this should not be updated
        if not self._blink_color == "red":
            self._blink_color = "red" if "(ERROR)" in message else "darkorange"

            pixmapi = QtWidgets.QStyle.StandardPixmap.SP_MessageBoxCritical if \
                "(ERROR)" in message else QtWidgets.QStyle.StandardPixmap.SP_MessageBoxWarning

            icon = self.style().standardIcon(pixmapi)
            self.tabs.setTabIcon(self.tabs.indexOf(self.log_widget), icon)

        # Start timer
        self._blink_qtimer.start(500)
