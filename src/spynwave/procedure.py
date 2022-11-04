"""
This file is part of the SpynWave package.
"""

import logging

from time import time, sleep
from datetime import datetime

from pymeasure.experiment import Procedure, Parameter, FloatParameter, BooleanParameter, \
    IntegerParameter, ListParameter, Metadata

from spynwave.drivers import Magnet, VNA

# Setup logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

# Instrument addresses
vna_address = "visa://131.155.124.201/TCPIP0::VS1513648::inst0::INSTR"


class PSWSProcedure(Procedure):
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
        default="2-port"
    )
    measurement_type = ListParameter(
        "Type of measurement",
        choices=[
            "Field sweep",
            "Frequency sweep",
        ],
        default="Frequency sweep"
    )
    averages = IntegerParameter(
        "Number of averages",
        default=2,
        minimum=1,
    )
    average_type = ListParameter(
        "Averaging type",
        choices=[
            "point-by-point",
            "sweep-by-sweep",
        ],
        default="sweep-by-sweep",
    )
    # average_nr = IntegerParameter(
    #     "Average number",
    #     default=0,
    # )

    # Basic parameters
    rf_frequency = FloatParameter(
        "RF Frequency",
        default=15e9,
        minimum=0,  # TODO: find minimum frequency
        maximum=40e9,  # TODO: find maximum frequency
        units="Hz",
        group_by="measurement_type",
        group_condition=lambda v: v != "Frequency sweep",
    )

    magnetic_field = FloatParameter(
        "Magnetic field",
        default=0,
        minimum=-1,  # TODO: find minimum field
        maximum=+1,  # TODO: find maximum field
        units="T",
        group_by="measurement_type",
        group_condition=lambda v: v != "Field sweep",
    )

    # VNA settings
    rf_power = FloatParameter(
        "RF output power",
        units="dBm",
        default=0,
        minimum=-30,  # TODO: find minimum power
        maximum=+20,  # TODO: find maximum power
    )
    rf_bandwidth = FloatParameter(
        "RF bandwidth",
        units="Hz",
        default=100,
        minimum=1,  # TODO: find minimum bandwidth
        maximum=1e6,  # TODO: find maximum bandwidth
    )

    # Frequency sweep settings
    frequency_start = FloatParameter(
        "Start frequency",
        default=5e9,
        minimum=0,  # TODO: find minimum frequency
        maximum=40e9,  # TODO: find maximum frequency
        units="Hz",
        group_by="measurement_type",
        group_condition="Frequency sweep",
    )
    frequency_stop = FloatParameter(
        "Stop frequency",
        default=15e9,
        minimum=0,  # TODO: find minimum frequency
        maximum=40e9,  # TODO: find maximum frequency
        units="Hz",
        group_by="measurement_type",
        group_condition="Frequency sweep",
    )
    frequency_points = IntegerParameter(
        "Frequency points",
        default=201,
        minimum=1,  # TODO: find minimum frequency steps
        maximum=100000,  # TODO: find maximum frequency steps
        group_by="measurement_type",
        group_condition="Frequency sweep",
    )


    # Metadata to be stored in the file
    measurement_date = Metadata("Measurement date", fget=datetime.now)
    start_time = Metadata("Measurement timestamp", fget=time)

    # TODO: query calibration status, date, and (possibly) other atributes

    # Define data columns
    DATA_COLUMNS = [
        "Timestamp (s)",
        "Field (T)",
        "Frequency (Hz)",
        "S11 real",
        "S11 imag",
        "S21 real",
        "S21 imag",
        "S12 real",
        "S12 imag",
        "S22 real",
        "S22 imag",
    ]

    # initiate instrument attributes
    vna = None
    magnet = None

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
        self.vna = VNA(vna_address)
        # self.magnet = Magnet()

        ## Run general startup procedure
        self.vna.startup()
        self.vna.set_measurement_ports(self.measurement_ports)
        self.vna.general_measurement_settings(
            bandwidth=self.rf_bandwidth,
            power_level=self.rf_power,
        )
        self.vna.configure_averaging(
            enabled=True,
            average_count=self.averages,
            averaging_type=self.average_type,
        )

        # self.magnet.startup()

        ## Run measurement-type-specific startup
        if self.measurement_type == "Frequency sweep":
            self.vna.prepare_frequency_sweep(
                frequency_start=self.frequency_start,
                frequency_stop=self.frequency_stop,
                frequency_points=self.frequency_points,
            )
        else:
            raise NotImplementedError(f"Measurement type {self.measurement_type} "
                                      f"not yet implemented")

        self.vna.reset_to_measure()

    # Define measurement procedure
    def execute(self):
        """ Execute the actual measurement. Here only the global outline of
        the measurement is defined, all the actual activities are handled by
        helper functions (in the helpers section of this class).
        """
        if self.measurement_type == "Frequency sweep":
            self.execute_frequency_sweep()
        else:
            raise NotImplementedError(f"Measurement type {self.measurement_type} "
                                      f"not yet implemented")

    def execute_frequency_sweep(self):
        self.vna.trigger_frequency_sweep()
        start = time()
        while not self.should_stop():
            cnt = self.vna.ch_1.average_sweep_count
            self.emit("progress", cnt/self.averages * 100)
            if cnt >= self.averages:
                break
            self.sleep()
        stop = time()

        data = self.vna.grab_data()

        data["Timestamp (s)"] = (stop + start) / 2

        self.emit("results", data)

    def get_datapoint(self):
        data = {
            "Timestamp (s)": time(),
        }

        return data

    # Define stop sequence
    def shutdown(self):
        """ Wrap up the measurement.
        """

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

    # def get_estimates(self, sequence_length=0):
    #     estimates = list()
    #     return estimates
