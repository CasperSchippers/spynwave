import logging

from pymeasure.instruments import Instrument
from pymeasure.instruments.validators import (
    strict_discrete_set,
    strict_range
)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class BrukerBEC1(Instrument):
    """ A class representing the Bruker B-EC1 magnet power supply controller.
    """

    def __init__(self, adapter, **kwargs):
        super().__init__(
            adapter,
            "Bruker B-EC1 magnet power supply controller",
            includeSCPI=False,
            **kwargs,
        )

    remote_enabled = Instrument.measurement(
        "REM/",
        """ A xxx property that returns the local/remote state of the instrument.
        """,
    )

    DC_power_enabled = Instrument.control(
        "DCP/", "DCP=%d",
        """ A bool property that controls whether the dc power is enabled. Can be set.
        """,
        values={True: 1, False: 0},
        map_values=True,
    )

    current = Instrument.control(
        "CUR/", "CUR=%f",
        """ A float property that controls the output current in amps. Can be set
        """,
    )

    polarity = Instrument.control(
        "POL/", "POL=%d",
        """ A string property that controls the polarity of the power supply. Valid values are 
        "positive" and "negative". The property can also return "no reversal unit" and "unit busy".
        Can be set.
        """,
        values={"positive": 1, "negative": 2, "no reversal unit": 0, "unit busy": 3},
        map_values=True,
    )

    output_current = Instrument.measurement(
        "CHN/",
        """ A property that returns the output current in amps.
        """,
    )

    output_voltage = Instrument.measurement(
        "VLT/",
        """ A property that returns the output voltage.
        """,
    )

    magnet_resistance = Instrument.measurement(
        "RES/",
        """ A property that returns the magnet resistance.
        """,
    )

    power_stage_temperature = Instrument.measurement(
        "TEM/",
        """ A property that returns the power stage temperature (in celsius), if installed.
        """,
    )

    uce_voltage = Instrument.measurement(
        "UCE/",
        """ A property that returns the Uce voltage, if installed.
        """,
    )

    external_reference = Instrument.control(
        "EXT/", "EXT=%d",
        """ A string property that controls the reference source. Valid values are "internal",
        "external", and "BH-15". Can be set.
        """,
        values={"internal": 0, "external": 1, "BH-15": 2},
        map_values=True,
    )

    def reset_error_message(self):
        """ Reset the error messages.
        """
        self.write("RST=0")

    # TODO: this requires a bit more work to get it right I guess
    status = Instrument.control(
        "STA/", "STA=%d",
        """ A property that reads the information about the power supply's status. If set to 0, the
        command flow is reset.
        """,
        values=[0],
        validator=strict_discrete_set,
    )

    def reset_command_flow(self):
        """ Reset the command flow.
        """
        self.status = 0

    cycle_state = Instrument.control(
        "CYC/", "CYC=%d",
        """ A string property that controls the cycle state. Valid values are "running", "stopped",
        and "interrupted". Can be set. 
        """,
        values={"running": 1, "stopped": 0, "interrupted": 2},
        map_values=True,
    )

    cycle_current_up = Instrument.control(
        "CCU/", "CCU=%f",
        """ A float property that controls the cycle current up (in amps). Can be set 
        """,
    )

    cycle_current_down = Instrument.control(
        "CCD/", "CCD=%f",
        """ A float property that controls the cycle current down (in amps). Can be set 
        """,
    )

    cycle_rate_up = Instrument.control(
        "RCU/", "RCU=%f",
        """ A float property that controls the cycle current up rate (in amps). Can be set 
        """,
    )

    cycle_rate_down = Instrument.control(
        "RCD/", "RCD=%f",
        """ A float property that controls the cycle current down rate (in amps). Can be set 
        """,
    )

    cycle_time_up = Instrument.control(
        "WCU/", "WCU=%f",
        """ A float property that controls the cycle time up (in seconds). Can be set.
        """,
    )

    cycle_time_up_remaining = Instrument.measurement(
        "TIU/",
        """ A float property that returns the remaining cycle time up (in seconds).
        """,
    )

    cycle_time_down = Instrument.control(
        "WCD/", "WCD=%f",
        """ A float property that controls the cycle time up (in seconds). Can be set.
        """,
    )

    cycle_time_down_remaining = Instrument.measurement(
        "TID/",
        """ A float property that returns the remaining cycle time up (in seconds).
        """,
    )

    number_of_cycles = Instrument.control(
        "WCD/", "WCD=%f",
        """ An int property that controls the number of cycles to perform. Valid values are between
        0 and 65536 cycles. Can be set.
        """,
        values=[0, 65536],
        validator=strict_range,
    )

    number_of_cycles_remaining = Instrument.measurement(
        "TID/",
        """ An int property that returns the remaining number of cycles.
        """,
    )
