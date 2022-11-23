"""
This file is part of the SpynWave package.
"""

import logging

from time import time, sleep
from datetime import datetime

import numpy as np

from pymeasure.experiment import (
    Procedure, Parameter, FloatParameter, BooleanParameter,
    IntegerParameter, Metadata
)

from spynwave.drivers import Magnet

# Setup logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())


class MagnetCalibrationProcedure(Procedure):
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

    symmetric_currents = BooleanParameter(
        "Use symmetric currents",
        default=True,
    )

    max_current = FloatParameter(
        "Maximum current",
        default=+10,
        step=1,
        units="A",
    )

    min_current = FloatParameter(
        "Minimum current",
        default=-10,
        step=1,
        units="A",
        group_by="symmetric_currents",
        group_condition=False,
    )

    current_steps = FloatParameter(
        "Current steps",
        default=1,
        step=0.1,
        minimum=0,
        units="A",
    )

    dwell_time = FloatParameter(
        "Dwell time",
        default=2,
        minimum=0,
        units="s",
        )

    number_of_sweeps = IntegerParameter(
        "Number of sweeps",
        default=1,
        minimum=1,
    )

    # Metadata to be stored in the file
    measurement_date = Metadata("Measurement date", fget=datetime.now)
    start_time = Metadata("Measurement timestamp", fget=time)

    # Define data columns
    DATA_COLUMNS = [
        "Timestamp (s)",
        "Current (A)",
        "Field (T)"
    ]

    # initialize instrument attributes
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
        # Connect to instruments
        # self.magnet = Magnet(mirror_fields=self.mirrored_field,
        #                      measurement_type=self.measurement_type)

        # Run general startup procedure
        # self.magnet.startup()

    # Define measurement procedure
    def execute(self):
        """ Execute the actual measurement. Here only the global outline of
        the measurement is defined, all the actual activities are handled by
        helper functions (in the helpers section of this class).
        """
        fieldlist = self.get_fieldlist()


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

        # if self.magnet is not None:
        #     self.magnet.shutdown()

    r"""
         _    _   ______   _        _____    ______   _____     _____
        | |  | | |  ____| | |      |  __ \  |  ____| |  __ \   / ____|
        | |__| | | |__    | |      | |__) | | |__    | |__) | | (___
        |  __  | |  __|   | |      |  ___/  |  __|   |  _  /   \___ \
        | |  | | | |____  | |____  | |      | |____  | | \ \   ____) |
        |_|  |_| |______| |______| |_|      |______| |_|  \_\ |_____/

    """

    def get_fieldlist(self):
        start = -self.max_current if self.symmetric_currents else self.min_current
        stop = +self.max_current
        step = self.current_steps
        if start > stop:
            step *= -1

        field_points = np.arange(start, stop + step / 2, step)

        field_points = np.concatenate([
            field_points, field_points[::-1]
        ] * self.number_of_sweeps)

        return field_points

    def sleep(self, duration=0.1):
        start = time()
        while time() - start < duration and not self.should_stop():
            sleep(0.01)

    def get_estimates(self):
        estimates = self.number_of_sweeps * len(self.get_fieldlist()) * self.dwell_time
        return estimates
