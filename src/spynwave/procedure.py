import logging

from time import time, sleep

from pymeasure.experiment import Procedure, Parameter, FloatParameter, BooleanParameter, \
    IntegerParameter, ListParameter, Metadata

# Setup logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

# Instrument addresses
gpib_address = "GPIB::"
k2700_address = gpib_address + "30"
k6221_address = gpib_address + "13"
mfli_id = "dev4285"  # for probing with MFLI
sr830_address = gpib_address + "06"  # for probing with SR830
itc503_address = gpib_address + "23"  # for temperature control with ITC503
delta_address = gpib_address + "08"  # for magnetic field control with delta elektronica SM7045D


class PSWSProcedure(Procedure):
    r"""
     _____        _____            __  __ ______ _______ ______ _____   _____
    |  __ \ /\   |  __ \     /\   |  \/  |  ____|__   __|  ____|  __ \ / ____|
    | |__) /  \  | |__) |   /  \  | \  / | |__     | |  | |__  | |__) | (___
    |  ___/ /\ \ |  _  /   / /\ \ | |\/| |  __|    | |  |  __| |  _  / \___ \
    | |  / ____ \| | \ \  / ____ \| |  | | |____   | |  | |____| | \ \ ____) |
    |_| /_/    \_\_|  \_\/_/    \_\_|  |_|______|  |_|  |______|_|  \_\_____/

    """
    AA_folder = Parameter(
        "Folder",
        default=".",
    )
    AB_filename_base = Parameter(
        "Filename base",
        default="PSWS",
    )

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
        "S22 imag",
        "S22 real",
    ]

    # initiate instrument attributes
    VNA = None
    k6221 = None
    zMFLI = None
    oxITC = None

    start_time = None

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


        self.start_time = time()

    # Define measurement procedure
    def execute(self):
        """ Execute the actual measurement. Here only the global outline of
        the measurement is defined, all the actual activities are handled by
        helper functions (in the helpers section of this class).
        """
        pass

    def get_datapoint(self):
        data = {
            "Timestamp (s)": time(),
        }

        return data

    # Define stop sequence
    def shutdown(self):
        """ Wrap up the measurement.
        """
        pass

    r"""
         _    _   ______   _        _____    ______   _____     _____
        | |  | | |  ____| | |      |  __ \  |  ____| |  __ \   / ____|
        | |__| | | |__    | |      | |__) | | |__    | |__) | | (___
        |  __  | |  __|   | |      |  ___/  |  __|   |  _  /   \___ \
        | |  | | | |____  | |____  | |      | |____  | | \ \   ____) |
        |_|  |_| |______| |______| |_|      |______| |_|  \_\ |_____/

    """

    def sleep(self, duration=None):
        if duration is None:
            duration = self.delay

        t0 = time()
        while time() - t0 < duration and not self.should_stop():
            sleep(0.01)

    def get_estimates(self, sequence_length=0):
        estimates = list()
        return estimates
