"""
This file is part of the SpynWave package.
"""

import logging

from pyvisa import VisaIOError
from pyvisa.constants import VI_ERROR_TMO

from pymeasure.experiment import Results, unique_filename
from pymeasure.display.Qt import QtGui
from pymeasure.display.widgets.dock_widget import DockWidget
from pymeasure.display.widgets import ImageWidget

# For patching the ResultsImage with a working method
from pymeasure.display.curves import ResultsImage

from spynwave.procedure import PSWSProcedure
from spynwave.drivers import VNA
from spynwave.widgets import SpynWaveWindowBase
from spynwave.pymeasure_patches.pandas_formatter import CSVFormatterPandas


# Setup logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())


class PSWSWindow(SpynWaveWindowBase):
    def __init__(self):
        self.dock_widget = DockWidget("Multiple graphs", PSWSProcedure,
                                      ["Field (T)"],
                                      ["S11 real", "S22 real"])

        self.image_widget = ImageWidget("2D plot", PSWSProcedure.DATA_COLUMNS,
                                        "field", "frequency", "S11 real")
        self.image_widget.x_column_name = "Field (T)"
        self.image_widget.y_column_name = "Frequency (Hz)"

        super().__init__(
            procedure_class=PSWSProcedure,
            inputs=(
                "measurement_type",
                "rf_frequency",
                "magnetic_field",
                "frequency_start",
                "frequency_end",
                "frequency_step",
                "frequency_averages",
                "field_start",
                "field_end",
                "field_ramp_rate",
                "time_duration",
                "dc_excitation",
                "dc_regulate",
                "dc_voltage_start",
                "dc_voltage_end",
                "dc_voltage_rate",
                "dc_current_start",
                "dc_current_end",
                "dc_current_rate",
                "dc_voltage",
                "dc_current",
                "dc_voltage_compliance",
                "dc_current_compliance",
                "saturate_field_before_measurement",
                "saturation_field",
                "rf_advanced_settings",
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
            widget_list=(self.dock_widget, self.image_widget)
        )

        # self.update_inputs_from_vna()

        # Link the dc excitation checkbox to the measurement type
        # Required for some dc-sweep parameters to show up
        self.inputs.measurement_type.currentTextChanged.connect(self._set_dc_excitation)
        self._set_dc_excitation(self.inputs.measurement_type.currentText())

    def queue(self, procedure=None):
        if procedure is None:
            procedure = self.make_procedure()

        folder = self.directory
        filename = self.filename
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

    #################################################################
    # Methods below extend the ManagedWindow with custom components #
    #################################################################

    _old_dc_checked_state = None

    def _set_dc_excitation(self, value):
        if value == "DC sweep":
            self._old_dc_checked_state = self.inputs.dc_excitation.isChecked()
            self.inputs.dc_excitation.setChecked(True)
        elif self._old_dc_checked_state is not None:
            self.inputs.dc_excitation.setChecked(self._old_dc_checked_state)
            self._old_dc_checked_state = None

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

        # self.inputs.frequency_step.setMaximum(frequency_steps)
        step = (frequency_max - frequency_min) / frequency_steps
        self.inputs.frequency_step.setValue(step)
        self.inputs.frequency_step.setSingleStep(step)

        self.inputs.rf_frequency.setMinimum(frequency_min)
        self.inputs.rf_frequency.setMaximum(frequency_max)
        self.inputs.rf_frequency.setValue(frequency_cw)

        self.inputs.rf_bandwidth.setValue(bandwidth)
        self.inputs.rf_power.setValue(power_level)


# Monkeypatch the ResultsImage, because it is not working correctly presently
def scale(self, x, y):
    tr = QtGui.QTransform()  # prepare ImageItem transformation:
    tr.scale(x, y)
    self.setTransform(tr)


def translate(self, x, y):
    tr = QtGui.QTransform()  # prepare ImageItem transformation:
    tr.translate(x, y)
    self.setTransform(tr)


ResultsImage.scale = scale
ResultsImage.translate = translate


def new_curve(self, results, color=None, **kwargs):
    """ Creates a new image """
    try:
        image = ResultsImage(results,
                             wdg=self,
                             x=self.image_frame.x_axis,
                             y=self.image_frame.y_axis,
                             z=self.image_frame.z_axis,
                             **kwargs
                             )

        image.x = self.x_column_name
        image.y = self.y_column_name

        scales = {"field": 1e-3, "frequency": 1e9}
        image.xstart *= scales[self.image_frame.x_axis]
        image.xend *= scales[self.image_frame.x_axis]
        image.xstep *= scales[self.image_frame.x_axis]
        image.ystart *= scales[self.image_frame.y_axis]
        image.yend *= scales[self.image_frame.y_axis]
        image.ystep *= scales[self.image_frame.y_axis]

        image.scale(image.xstep, image.ystep)
        image.translate(int(image.xstart / image.xstep) - 0.5,
                        int(image.ystart / image.ystep) - 0.5)

        return image
    except Exception as exc:
        log.warning(f"Could not create an image for some reason, continuing without: {exc}")
        return None


ImageWidget.new_curve = new_curve
