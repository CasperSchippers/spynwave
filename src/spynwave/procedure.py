"""
This file is part of the SpynWave package.
"""

import logging

from time import time, sleep
from datetime import datetime

from pymeasure.experiment import (
    Procedure, Parameter, FloatParameter, BooleanParameter,
    ListParameter, Metadata
)

from spynwave.drivers import Magnet, VNA, SourceMeter
from spynwave.procedures import MixinFieldSweep, MixinFrequencySweep, MixinTimeSweep

# Setup logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())


class PSWSProcedure(MixinFieldSweep, MixinFrequencySweep, MixinTimeSweep, Procedure):
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
            "Time sweep",
        ],
        default="Field sweep"
    )

    # Basic parameters
    rf_frequency = FloatParameter(
        "CW Frequency",
        default=15,
        minimum=0,
        maximum=40,
        step=1,
        units="GHz",
        group_by="measurement_type",
        group_condition=lambda v: v != "Frequency sweep",
    )

    magnetic_field = FloatParameter(
        "Magnetic field",
        default=0,
        # minimum=-686,
        # maximum=+686,
        step=1,
        units="mT",
        group_by="measurement_type",
        group_condition=lambda v: v != "Field sweep",
    )

    mirrored_field = BooleanParameter(
        "Perform with mirrored field",
        default=False,
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

    saturate_field_before_measurement = BooleanParameter(
        "Saturate field before measurement",
        default=True,
    )
    saturation_field = FloatParameter(
        "Saturation field",
        default=200,
        # minimum=-686,
        # maximum=+686,
        step=1,
        units="mT",
        group_by="saturate_field_before_measurement",
        group_condition=True,
    )
    saturation_time = FloatParameter(
        "Saturation ",
        default=2,
        minimum=0,
        maximum=120,
        step=1,
        units="s",
        group_by="saturate_field_before_measurement",
        group_condition=True,
    )

    dc_control = ListParameter(
        "Apply DC excitation",
        choices=[False, "Voltage", "Current"],
        default=False,
    )

    # Metadata to be stored in the file
    measurement_date = Metadata("Measurement date", fget=datetime.now)
    start_time = Metadata("Measurement timestamp", fget=time)
    magnet_setup = Metadata("Magnet calibrated for", fget="magnet.name")
    VNA_calibrated = Metadata("VNA calibrated", fget="vna.vectorstar.ch_1.calibration_enabled")
    VNA_bandwidth = Metadata("RF bandwidth", fget="vna.vectorstar.ch_1.bandwidth", units="Hz")
    VNA_powerlevel = Metadata("RF power level", fget="vna.vectorstar.ch_1.pt_1.power_level",
                              units="dBm")
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
    source_meter = None

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
        # Connect to instruments
        freq_sweep = self.measurement_type == "Frequency sweep"
        self.vna = VNA(use_DAQmx=False if freq_sweep else None)
        self.magnet = Magnet(mirror_fields=self.mirrored_field,
                             measurement_type=self.measurement_type)

        if self.dc_control:
            self.source_meter = SourceMeter()

        # Run general startup procedure
        self.vna.startup()
        self.vna.set_measurement_ports(self.measurement_ports)
        if self.rf_advanced_settings:
            self.vna.general_measurement_settings(
                bandwidth=self.rf_bandwidth,
                power_level=self.rf_power,
            )
        # TODO: Maybe this needs to be measurement-type
        self.magnet.startup()

        self.source_meter.startup()

        if self.saturate_field_before_measurement:
            self.saturate_field()

        # Run measurement-type-specific startup
        self.get_mixin_method('startup')()

        self.vna.reset_to_measure()

    # Define measurement procedure
    def execute(self):
        """ Execute the actual measurement. Here only the global outline of
        the measurement is defined, all the actual activities are handled by
        helper functions (in the helpers section of this class).
        """
        self.get_mixin_method('execute')()

    # def get_datapoint(self):
    #     data = {
    #         "Timestamp (s)": time(),
    #         "Field (T)": self.magnet.measure_field()
    #     }
    #
    #     return data

    # Define stop sequence
    def shutdown(self):
        """ Wrap up the measurement.
        """

        # Perform a measurement-specific shutdown, if necessary
        self.get_mixin_method('shutdown')()

        if self.vna is not None:
            self.vna.shutdown()

        if self.magnet is not None:
            self.magnet.shutdown()

        if self.source_meter is not None:
            self.source_meter.shutdown()

    r"""
         _    _   ______   _        _____    ______   _____     _____
        | |  | | |  ____| | |      |  __ \  |  ____| |  __ \   / ____|
        | |__| | | |__    | |      | |__) | | |__    | |__) | | (___
        |  __  | |  __|   | |      |  ___/  |  __|   |  _  /   \___ \
        | |  | | | |____  | |____  | |      | |____  | | \ \   ____) |
        |_|  |_| |______| |______| |_|      |______| |_|  \_\ |_____/

    """

    def saturate_field(self):
        # Saturate the magnetic field (after saturation, go already to the starting field
        self.magnet.set_field(self.saturation_field * 1e-3)
        self.magnet.wait_for_stable_field(interval=2, timeout=60, should_stop=self.should_stop)
        self.sleep(self.saturation_time)

    def get_mixin_method(self, base_method):
        spec = str(self.measurement_type).replace(" ", "_").lower()
        method_name = f"{base_method}_{spec}"
        if hasattr(self, method_name):
            return getattr(self, method_name)
        else:
            raise NotImplementedError(f"Measurement type {self.measurement_type} "
                                      f"not implemented (or missing {base_method}).")

    def sleep(self, duration=0.1):
        start = time()
        while time() - start < duration and not self.should_stop():
            sleep(0.01)

    def get_estimates(self):
        estimates = self.get_mixin_method('get_estimates')()
        return estimates
