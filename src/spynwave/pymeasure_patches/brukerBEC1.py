import logging
from enum import IntFlag

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
            asrl=dict(
                baud_rate=9600,
                data_bits=8,
                stop_bits=10,
                parity=1,
                write_termination='\r',
                # write_termination='\n',
            ),
            # gpib=dict(),
            **kwargs,
        )

    class ERRORS(IntFlag):
        """ Enum element for error decoding
        """
        FUNCTION = 1  # Function not supported, also e.g. during polarity reversal
        ARGUMENT = 2  # The argument contains unknown characters
        PORT_NOT_AVAILABLE = 3  # Port not available
        LOCAL_ERROR = 4  # Access denied, check the local / remote switch
        RANGE_ERROR = 5  # The argument is out of the allowed range
        REF_ERROR = 6  # Access denied, Ext Ref or BH-15 active
        ERROR_PENDING = 7  # DC command denied, there is still an error pending
        CYCLE_ERROR = 8  # Access denied, cycle is active
        DC_ERROR = 9  # Access denied, DC power is off

    def check_errors(self):
        """ Read the error message from the instrument, by reading the echo after a write command
        """
        message = self.read()
        error = self.check_response_for_error(message)
        return error

    def check_response_for_error(self, message):
        print(message)
        if isinstance(message, str) and message.startswith("E"):
            error_code = int(message[1:])
            error = self.ERRORS(error_code)
            log.error(error)
            print(error)
            return error
        return message

    remote_enabled = Instrument.measurement(
        "REM/",
        """ A xxx property that returns the local/remote state of the instrument.
        """,
        values={True: 1, False: 0},
        map_values=True,
        check_set_errors=True,
    )

    DC_power_enabled = Instrument.control(
        "DCP/", "DCP=%d",
        """ A bool property that controls whether the dc power is enabled. Can be set.
        """,
        values={True: 1, False: 0},
        map_values=True,
        check_set_errors=True,
        get_process=check_response_for_error,
    )

    current = Instrument.control(
        "CUR/", "CUR=%f",
        """ A float property that controls the output current in amps. Can be set
        """,
        check_set_errors=True,
        get_process=check_response_for_error,
    )

    polarity = Instrument.control(
        "POL/", "POL=%d",
        """ A string property that controls the polarity of the power supply. Valid values are
        "positive" and "negative". The property can also return "no reversal unit" and "unit busy".
        Can be set.
        """,
        values={"positive": 1, "negative": 2, "no reversal unit": 0, "unit busy": 3},
        map_values=True,
        check_set_errors=True,
        get_process=check_response_for_error,
    )

    output_current = Instrument.measurement(
        "CHN/",
        """ A property that returns the output current in amps.
        """,
        get_process=check_response_for_error,
    )

    output_voltage = Instrument.measurement(
        "VLT/",
        """ A property that returns the output voltage.
        """,
        get_process=check_response_for_error,
    )

    magnet_resistance = Instrument.measurement(
        "RES/",
        """ A property that returns the magnet resistance.
        """,
        get_process=check_response_for_error,
    )

    power_stage_temperature = Instrument.measurement(
        "TEM/",
        """ A property that returns the power stage temperature (in celsius), if installed.
        """,
        get_process=check_response_for_error,
    )

    uce_voltage = Instrument.measurement(
        "UCE/",
        """ A property that returns the Uce voltage, if installed.
        """,
        get_process=check_response_for_error,
    )

    external_reference = Instrument.control(
        "EXT/", "EXT=%d",
        """ A string property that controls the reference source. Valid values are "internal",
        "external", and "BH-15". Can be set.
        """,
        values={"internal": 0, "external": 1, "BH-15": 2},
        map_values=True,
        check_set_errors=True,
        get_process=check_response_for_error,
    )

    def reset_error_message(self):
        """ Reset the error messages.
        """
        self.write("RST=0")
        self.check_errors()

    # TODO: this requires a bit more work to get it right I guess
    status = Instrument.control(
        "STA/", "STA=%d",
        """ A property that reads the information about the power supply's status. If set to 0, the
        command flow is reset.
        """,
        values=[0],
        validator=strict_discrete_set,
        check_set_errors=True,
        get_process=check_response_for_error,
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
        check_set_errors=True,
        get_process=check_response_for_error,
    )

    cycle_current_up = Instrument.control(
        "CCU/", "CCU=%f",
        """ A float property that controls the cycle current up (in amps). Can be set.
        """,
        check_set_errors=True,
        get_process=check_response_for_error,
    )

    cycle_current_down = Instrument.control(
        "CCD/", "CCD=%f",
        """ A float property that controls the cycle current down (in amps). Can be set.
        """,
        check_set_errors=True,
        get_process=check_response_for_error,
    )

    cycle_rate_up = Instrument.control(
        "RCU/", "RCU=%f",
        """ A float property that controls the cycle current up rate (in amps). Can be set.
        """,
        check_set_errors=True,
        get_process=check_response_for_error,
    )

    cycle_rate_down = Instrument.control(
        "RCD/", "RCD=%f",
        """ A float property that controls the cycle current down rate (in amps). Can be set.
        """,
        check_set_errors=True,
        get_process=check_response_for_error,
    )

    cycle_time_up = Instrument.control(
        "WCU/", "WCU=%f",
        """ A float property that controls the cycle time up (in seconds). Can be set.
        """,
        check_set_errors=True,
        get_process=check_response_for_error,
    )

    cycle_time_up_remaining = Instrument.measurement(
        "TIU/",
        """ A float property that returns the remaining cycle time up (in seconds).
        """,
        get_process=check_response_for_error,
    )

    cycle_time_down = Instrument.control(
        "WCD/", "WCD=%f",
        """ A float property that controls the cycle time up (in seconds). Can be set.
        """,
        check_set_errors=True,
        get_process=check_response_for_error,
    )

    cycle_time_down_remaining = Instrument.measurement(
        "TID/",
        """ A float property that returns the remaining cycle time up (in seconds).
        """,
        get_process=check_response_for_error,
    )

    number_of_cycles = Instrument.control(
        "WCD/", "WCD=%f",
        """ An int property that controls the number of cycles to perform. Valid values are between
        0 and 65536 cycles. Can be set.
        """,
        values=[0, 65536],
        validator=strict_range,
        check_set_errors=True,
        get_process=check_response_for_error,
    )

    number_of_cycles_remaining = Instrument.measurement(
        "TID/",
        """ An int property that returns the remaining number of cycles.
        """,
        get_process=check_response_for_error,
    )
