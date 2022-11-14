"""
This file is part of the SpynWave package.
"""

import logging

from time import time, sleep
from datetime import datetime

from pymeasure.experiment import (
    Procedure, Parameter, FloatParameter, BooleanParameter,
    IntegerParameter, ListParameter, Metadata
)

from spynwave.drivers import Magnet, VNA
from spynwave.procedures import MixinFieldSweep, MixinFrequencySweep

# Setup logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class PSWSProcedure(MixinFieldSweep, MixinFrequencySweep, Procedure):
    r"""
     _____        _____            __  __ ______ _______ ______ _____   _____
    |  __ \ /\   |  __ \     /\   |  \/  |  ____|__   __|  ____|  __ \ / ____|
    | |__) /  \  | |__) |   /  \  | \  / | |__     | |  | |__  | |__) | (___
    |  ___/ /\ \ |  _  /   / /\ \ | |\/| |  __|    | |  |  __| |  _  / \___ \
    | |  / ____ \| | \ \  / ____ \| |  | | |____   | |  | |____| | \ \ ____) |
    |_| /_/    \_\_|  \_\/_/    \_\_|  |_|______|  |_|  |______|_|  \_\_____/

    """

    # Filename and folder
    AA_folder = Parameter(
        "Folder",
        default=".",
    )
    AB_filename_base = Parameter(
        "Filename base",
        default="PSWS",
    )

    # General measurement settings
    measurement_ports = ListParameter(
        "Measurement ports",
        choices=[
            "2-port",
            "1-port: S11",
            "1-port: S22",
        ],
        default="2-port",
        group_by="rf_advanced_settings",
    )
    measurement_type = ListParameter(
        "Type of measurement",
        choices=[
            "Field sweep",
            "Frequency sweep",
        ],
        default="Field sweep"
    )
    # average_nr = IntegerParameter(
    #     "Average number",
    #     default=0,
    # )

    # Basic parameters
    rf_frequency = FloatParameter(
        "CW Frequency",
        default=15e9,
        minimum=0,
        maximum=40e9,
        units="Hz",
        group_by="measurement_type",
        group_condition=lambda v: v != "Frequency sweep",
    )

    magnetic_field = FloatParameter(
        "Magnetic field",
        default=0,
        minimum=-0.686,
        maximum=+0.686,
        units="T",
        group_by="measurement_type",
        group_condition=lambda v: v != "Field sweep",
    )

    # VNA settings
    rf_advanced_settings = BooleanParameter(
        "Advanced RF settings",
        default=False,
    )
    rf_power = FloatParameter(
        "RF output power",
        units="dBm",
        default=0,
        minimum=-30,
        maximum=+30,
        group_by="rf_advanced_settings",
    )
    rf_bandwidth = FloatParameter(
        "RF bandwidth",
        units="Hz",
        default=100,
        minimum=1,
        maximum=1e6,
        group_by="rf_advanced_settings",
    )
    average_type = ListParameter(
        "Averaging type",
        choices=[
            "point-by-point",
            "sweep-by-sweep",
        ],
        default="sweep-by-sweep",
        group_by="rf_advanced_settings",
    )

    # Metadata to be stored in the file
    measurement_date = Metadata("Measurement date", fget=datetime.now)
    start_time = Metadata("Measurement timestamp", fget=time)
    VNA_calibrated = Metadata("VNA calibrated", fget="vna.vectorstar.calibration_enabled")
    # TODO: query calibration status, date, and (possibly) other attributes

    # Define data columns
    DATA_COLUMNS = [
        "Timestamp (s)",
        "Field (T)",
        "Frequency (Hz)",
        "Temperature (K)",
        "DC voltage (V)",
        "DC current (A)",
        "DC resistance (ohm)",
        "S11 real",
        "S11 imag",
        "S21 real",
        "S21 imag",
        "S12 real",
        "S12 imag",
        "S22 real",
        "S22 imag",
    ]

    # initialize instrument attributes
    vna = None
    magnet = None
    data_thread = None

    r"""
          ____    _    _   _______   _        _____   _   _   ______
         / __ \  | |  | | |__   __| | |      |_   _| | \ | | |  ____|
        | |  | | | |  | |    | |    | |        | |   |  \| | | |__
        | |  | | | |  | |    | |    | |        | |   | . ` | |  __|
        | |__| | | |__| |    | |    | |____   _| |_  | |\  | | |____
         \____/   \____/     |_|    |______| |_____| |_| \_| |______|

    """

    # Define start-up sequence
    def startup(self):
        """ Set up the properties and devices required for the measurement.
        The devices are connected and the default parameters are set.
        """
        ## Connect to instruments
        self.vna = VNA()
        self.magnet = Magnet()

        ## Run general startup procedure
        self.vna.startup()
        self.vna.set_measurement_ports(self.measurement_ports)
        self.vna.general_measurement_settings(
            bandwidth=self.rf_bandwidth,
            power_level=self.rf_power,
        )
        # TODO: Maybe this needs to be measurement-type
        self.magnet.startup()

        ## Run measurement-type-specific startup
        if self.measurement_type == "Frequency sweep":
            self.startup_frequency_sweep()
        elif self.measurement_type == "Field sweep":
            self.startup_field_sweep()
        else:
            raise NotImplementedError(f"Measurement type {self.measurement_type} "
                                      f"not implemented")

        self.vna.reset_to_measure()

    # Define measurement procedure
    def execute(self):
        """ Execute the actual measurement. Here only the global outline of
        the measurement is defined, all the actual activities are handled by
        helper functions (in the helpers section of this class).
        """
        if self.measurement_type == "Frequency sweep":
            self.execute_frequency_sweep()
        elif self.measurement_type == "Field sweep":
            self.execute_field_sweep()
        else:
            raise NotImplementedError(f"Measurement type {self.measurement_type} "
                                      f"not implemented")

    def get_datapoint(self):
        data = {
            "Timestamp (s)": time(),
            "Field (T)": self.magnet.measure_field()
        }

        return data

    # Define stop sequence
    def shutdown(self):
        """ Wrap up the measurement.
        """

        # Perform a measurement-specific shutdown, if necessary
        if self.measurement_type == "Frequency sweep":
            self.shutdown_frequency_sweep()
        elif self.measurement_type == "Field sweep":
            self.shutdown_field_sweep()
        else:
            raise NotImplementedError(f"Measurement type {self.measurement_type} "
                                      f"not implemented")

        if self.vna is not None:
            self.vna.shutdown()

        if self.magnet is not None:
            self.magnet.shutdown()

    r"""
         _    _   ______   _        _____    ______   _____     _____
        | |  | | |  ____| | |      |  __ \  |  ____| |  __ \   / ____|
        | |__| | | |__    | |      | |__) | | |__    | |__) | | (___
        |  __  | |  __|   | |      |  ___/  |  __|   |  _  /   \___ \
        | |  | | | |____  | |____  | |      | |____  | | \ \   ____) |
        |_|  |_| |______| |______| |_|      |______| |_|  \_\ |_____/

    """

    def sleep(self, duration=0.1):
        t0 = time()
        while time() - t0 < duration and not self.should_stop():
            sleep(0.01)

    def get_estimates(self, sequence_length=None):
        if self.measurement_type == "Frequency sweep":
            estimates = self.get_estimates_frequency_sweep(sequence_length)
        elif self.measurement_type == "Field sweep":
            estimates = self.get_estimates_field_sweep(sequence_length)
        else:
            raise NotImplementedError(f"Measurement type {self.measurement_type} "
                                      f"not implemented")

        return estimates
