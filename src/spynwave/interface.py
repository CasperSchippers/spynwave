"""
This file is part of the SpynWave package.
"""

import logging

from pyvisa import VisaIOError
from pyvisa.constants import VI_ERROR_TMO

from pymeasure.experiment import Results, unique_filename
from pymeasure.display.widgets.dock_widget import DockWidget
from pymeasure.display.widgets import ImageWidget

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

        # TODO: this can be added, but needs some work to get it running
        # self.image_widget = ImageWidget("2D plot", PSWSProcedure.DATA_COLUMNS,
        #                                 "field", "frequency", "S11 real")

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
                "time_duration",
                "frequency_averages",
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
            widget_list=(self.dock_widget, )
        )

        # self.update_inputs_from_vna()

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

    #################################################################
    # Methods below extend the ManagedWindow with custom components #
    #################################################################

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
