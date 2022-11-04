import logging

from pymeasure.instruments import Instrument, Channel
from pymeasure.instruments.validators import (
    strict_discrete_set,
    strict_range
)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

# TODO: check if this is still up to date with the channels implementation
class NestedChannel(Channel):
    def __init__(self, *args, placeholder='ch', **kwargs):
        self.placeholder = placeholder
        super().__init__(*args, **kwargs)

    class SafeDict(dict):
        def __missing__(self, key):
            return '{' + key + '}'

    def write(self, command, **kwargs):
        # TODO: check if ch="{ch}" is the best way to approach this
        self.parent.write(command.format_map(self.SafeDict({self.placeholder: self.id})), **kwargs)

    def write_binary_values(self, command, values, *args, **kwargs):
        self.parent.write_binary_values(command.format_map(self.SafeDict({self.placeholder: self.id})), values, *args, **kwargs)

    def check_errors(self):
        return self.parent.check_errors()


class Port(NestedChannel):
    power_level = Channel.control(
        "SOUR{ch}:POW:PORT{pt}?", "SOUR{ch}:POW:PORT{pt} %g",
        """ A float property that controls the power level (in dBm) of the indicated port on the
        indicated channel.
        """,  # TODO: check units: dB or dBm
        values=[-3E1, 3E1],
        validator=strict_range,
        check_get_errors=True,
        check_set_errors=True,
    )


class Trace(NestedChannel):
    SPARAM_LIST = ["S11", "S12", "S21", "S22",
                   "S13", "S23", "S33", "S31",
                   "S32", "S14", "S24", "S34",
                   "S41", "S42", "S43", "S44",]

    measurement_parameter = Channel.control(
        ":CALC{ch}:PAR{tr}:DEF?", ":CALC{ch}:PAR{tr}:DEF %s",
        """ A string property that controls the measurement parameter of the indicated trace. Can be
        set; valid values are any S-parameter (e.g. S11, S12, S41) for 4 ports, or one of the
        following:
        
        =====   ================================================================
        value   description
        =====   ================================================================
        Sxx     S-parameters (1-4 for both x)
        MIX     Response Mixed Mode
        NFIG    Noise Figure trace response (only with option 41 or 48)
        NPOW    Noise Power trace response (only with option 41 or 48)
        NTEMP   Noise Temperature trace response (only with option 41 or 48)
        AGA     Noise Figure Available Gain trace response (only with option 48)
        IGA     Noise Figure Insertion Gain trace response (only with option 48)
        =====   ================================================================
        
        
        """,
        values=SPARAM_LIST + ["MIX", "NFIG", "NPOW", "NTEMP", "AGA", "IGA"],
        validator=strict_discrete_set,
        check_get_errors=True,
        check_set_errors=True,
    )


class MeasurementChannel(NestedChannel):
    FREQUENCY_RANGE = [1E7, 4E10]
    TRACES = [1, 16]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for pt in range(self.parent.PORTS[1]):
            self.add_child(Port, pt + 1, collection="ports", prefix="pt", placeholder="pt")
        for tr in range(self.TRACES[1]):
            self.add_child(Trace, tr + 1, collection="traces", prefix="tr", placeholder="tr")

    def check_errors(self):
        return self.parent.check_errors()

    def activate(self):
        """ Sets the indicated channel as the active channel. """
        self.write(":DISP:WIND{ch}:ACT")

    number_of_traces = Channel.control(
        ":CALC{ch}:PAR:COUN?", ":CALC{ch}:PAR:COUN %d",
        """ An integer property that controls the number of traces on the specified channel. Valid
        values are between 1 and 16; can be set.
        """,
        values=TRACES,
        validator=strict_range,
        cast=int,
        check_get_errors=True,
        check_set_errors=True,
    )

    display_layout = Channel.control(
        ":DISP:WIND{ch}:SPL?", ":DISP:WIND{ch}:SPL %s",
        """ A string property that controls the trace display layout in a Row-by-Column format for
        the indicated channel. Can be set; valid values are: R1C1, R1C2, R2C1, R1C3, R3C1, R2C2C1,
        R2C1C2, C2R2R1, C2R1R2, R1C4, R4C1, R2C2, R2C3, R3C2, R2C4, R4C2, R3C3, R5C2, R2C5, R4C3,
        R3C4, R4C4. The number following the R indicates the number of rows, following the C the
        number of columns.
        """,
        values=["R1C1", "R1C2", "R2C1", "R1C3", "R3C1",
                "R2C2C1", "R2C1C2", "C2R2R1", "C2R1R2",
                "R1C4", "R4C1", "R2C2", "R2C3", "R3C2",
                "R2C4", "R4C2", "R3C3", "R5C2", "R2C5",
                "R4C3", "R3C4", "R4C4"],
        validator=strict_discrete_set,
        cast=int,
        check_get_errors=True,
        check_set_errors=True,
    )

    application_type = Channel.control(
        ":CALC{ch}:APPL:MEAS:TYP?", ":CALC{ch}:APPL:MEAS:TYP %s",
        """ A string property that controls the application type of the specified channel. Valid
        values are TRAN (for transmission/reflection), NFIG (for noise figure measurement), PULS
        (for PulseView). Can be set.""",
        values=["TRAN", "NFIG", "PULS"],
        validator=strict_discrete_set,
        check_get_errors=True,
        check_set_errors=True,
    )

    hold_function = Channel.control(
        ":SENS{ch}:HOLD:FUNC?", ":SENS{ch}:HOLD:FUNC %s",
        """ A string property that controls the hold function of the specified channel. Can be set; 
        valid values are:

        =====   =================================================
        value   description
        =====   =================================================
        CONT    Perform continuous sweeps on all channels
        HOLD    Hold the sweep on all channels
        SING    Perform a single sweep and then hold all channels
        =====   =================================================
        """,
        values=["CONT", "HOLD", "SING"],
        validator=strict_discrete_set,
        check_get_errors=True,
        check_set_errors=True,
    )

    frequency_start = Channel.control(
        ":SENS{ch}:FREQ:STAR?", ":SENS{ch}:FREQ:STAR %g",
        """ A float property that controls the start value of the sweep range of the indicated
        channel in hertz. Can be set; valid values are between 1E7 [Hz] (i.e. 10 MHz) and 4E10 [Hz]
        (i.e. 40 GHz). 
        """,
        values=FREQUENCY_RANGE,
        validator=strict_range,
        check_get_errors=True,
        check_set_errors=True,
    )

    frequency_stop = Channel.control(
        ":SENS{ch}:FREQ:STOP?", ":SENS{ch}:FREQ:STOP %g",
        """ A float property that controls the stop value of the sweep range of the indicated
        channel in hertz. Can be set; valid values are between 1E7 [Hz] (i.e. 10 MHz) and 4E10 [Hz]
        (i.e. 40 GHz). 
        """,
        values=FREQUENCY_RANGE,
        validator=strict_range,
        check_get_errors=True,
        check_set_errors=True,
    )

    frequency_span = Channel.control(
        ":SENS{ch}:FREQ:SPAN?", ":SENS{ch}:FREQ:SPAN %g",
        """ A float property that controls the span value of the sweep range of the indicated
        channel in hertz. Can be set; valid values are between 1E7 [Hz] (i.e. 10 MHz) and 4E10 [Hz]
        (i.e. 40 GHz). 
        """,
        values=FREQUENCY_RANGE,
        validator=strict_range,
        check_get_errors=True,
        check_set_errors=True,
    )

    frequency_center = Channel.control(
        ":SENS{ch}:FREQ:CENT?", ":SENS{ch}:FREQ:CENT %g",
        """ A float property that controls the center value of the sweep range of the indicated
        channel in hertz. Can be set; valid values are between 1E7 [Hz] (i.e. 10 MHz) and 4E10 [Hz]
        (i.e. 40 GHz). 
        """,
        values=FREQUENCY_RANGE,
        validator=strict_range,
        check_get_errors=True,
        check_set_errors=True,
    )

    frequency_CW = Channel.control(
        ":SENS{ch}:FREQ:CW?", ":SENS{ch}:FREQ:CW %g",
        """ A float property that controls the CW frequency of the indicated channel in hertz. Can
        be set; valid values are between 1E7 [Hz] (i.e. 10 MHz) and 4E10 [Hz] (i.e. 40 GHz). 
        """,
        values=FREQUENCY_RANGE,
        validator=strict_range,
        check_get_errors=True,
        check_set_errors=True,
    )

    def clear_average_count(self):
        """ Clears and restarts the averaging sweep count of the indicated channel. """
        self.write(":SENS{ch}:AVER:CLE")

    average_count = Channel.control(
        ":SENS{ch}:AVER:COUN?", ":SENS{ch}:AVER:COUN %d",
        """ An integer property that controls the averaging count for the indicated channel. The channel
        must be turned on. Valid values are between 1 and 1024; can be set.
        """,
        values=[1, 1024],
        validator=strict_range,
        cast=int,
        check_get_errors=True,
        check_set_errors=True,
    )

    average_sweep_count = Channel.measurement(
        ":SENS{ch}:AVER:SWE?",
        """ An integer property that returns the averaging sweep count for the indicated channel.
        """,
        cast=int,
        check_get_errors=True,
        check_set_errors=True,
    )

    average_type = Channel.control(
        ":SENS{ch}:AVER:TYP?", ":SENS{ch}:AVER:TYP %s",
        """ A string property that controls the averaging type to point-by-point (POIN) or
        sweep-by-sweep (SWE) for the indicated channel. Can be set. 
        """,
        values=["POIN", "SWE"],
        validator=strict_discrete_set,
        check_get_errors=True,
        check_set_errors=True,
    )

    averaging_enabled = Channel.control(
        ":SENS{ch}:AVER?", ":SENS{ch}:AVER %d",
        """ A boolean property that controls whether the averaging is turned on for the indicated
        channel. Can be set.
        """,
        values={True: 1, False: 0},
        map_values=True,
        check_get_errors=True,
        check_set_errors=True,
    )

    bandwidth = Channel.control(
        ":SENS{ch}:BWID?", ":SENS{ch}:BWID %g",
        """ A float property that controls the IF bandwidth for the indicated channel. Valid values
        are between 1 [Hz] and 1E6 [Hz] (i.e. 1 MHz). The system will automatically select the
        closest IF bandwidth from the available options (1, 3, 10 ... 1E5, 3E5, 1E6). Can be set.
        """,
        values=[1, 1E6],
        validator=strict_range,
        check_get_errors=True,
        check_set_errors=True,
    )


class AnritsuMS4644B(Instrument):
    """ A class representing the Anritsu MS4644B Vector Network Analyzer (VNA).

    """
    CHANNELS = [1, 16]
    TRACES = [1, 16]
    PORTS = [1, 4]  # TODO: check number: 4 or 7/8

    def __init__(self, adapter, **kwargs):
        super().__init__(
            adapter,
            "Anritsu MS4644B Vector Network Analyzer",
            **kwargs,
        )

        for ch in range(self.CHANNELS[1]):
            self.add_child(MeasurementChannel, ch+1)

    def check_errors(self):
        """ Read all errors from the instrument.

        :return: list of error entries
        """
        errors = []
        while True:
            err = self.values("SYST:ERR?")
            if err[0] != "No Error":
                log.error(f"{self.name}: {err[0]}")
                print(err)  # TODO: remove this line
                errors.append(err)
            else:
                break
        return errors

    output_data_format = Instrument.control(
        "FDHX?", "FDH%d",
        """ An integer property that controls the way the arbitrary block header for output data is
        formed. Can be set; valid values are:
        
        =====    ===========================================================
        value    description
        =====    ===========================================================
        0        A block header with arbitrary length will be sent. 
        1        The block header will have a fixed length of 11 characters.
        2        No block header will be sent. Not IEEE 488.2 compliant. 
        =====    ===========================================================
        """,
        values=[0, 1, 2],
        validator=strict_discrete_set,
        cast=int,
        check_get_errors=True,
        check_set_errors=True,
    )

    data_drawing_enabled = Instrument.control(
        "DD1?", "DD%d",  # TODO: see if there is an SCPI command for this
        """ A boolean property that controls whether data drawing is enabled (True) or not (False).
        Can be set.
        """,
        values={True: 1, False: 0},
        map_values=True,
        check_get_errors=True,
        check_set_errors=True,
    )

    event_status_enable_bits = Instrument.control(
        "*ESE?", "*ESE %d",
        """ An integer property that controls the Standard Event Status Enable Register bits (which
        can be queried using the ~`query_event_status_register` method). Can be set; valid values are
        between 0 and 255. Refer to the instrument manual for an explanation of the bits.
        """,
        values=[0, 255],
        validator=strict_range,
        cast=int,
        check_get_errors=True,
        check_set_errors=True,
    )

    def query_event_status_register(self):
        """ Query the value of the Standard Event Status Register. Note that querying this value,
        clears the register. Refer to the instrument manual for an explanation of the returned
        value.
        """
        return self.values("*ESR?", cast=int)[0]

    service_request_enable_bits = Instrument.control(
        "*SRE?", "*SRE %d",
        """ An integer property that controls the Service Request Enable Register bits. Can be set;
        valid values are between 0 and 255; setting 0 performs a register reset. Refer to the
        instrument manual for an explanation of the bits.
        """,
        values=[0, 255],
        validator=strict_range,
        cast=int,
        check_get_errors=True,
        check_set_errors=True,
    )

    installed_options = Instrument.measurement(
        "*OPT?",
        """ An integer property that returns the options that have been installed on the instrument.
        Refer to the user manual for explanation of the option numbers.
        """,
        cast=int,
    )

    def return_to_local(self):
        """ Returns the instrument to local operation. """
        self.write("RTL")

    binary_data_byte_order = Instrument.control(
        ":FORM:BORD?", ":FORM:BORD %s",
        """ A string property that controls the binary numeric I/O data byte order. Can be set;
        valid values are:
        
        =====   =========================================
        value   description
        =====   =========================================
        NORM    The most significant byte (MSB) is first
        SWAP    The least significant byte (LSB) is first
        =====   =========================================
        """,
        values=["NORM", "SWAP"],
        validator=strict_discrete_set,
        check_get_errors=True,
        check_set_errors=True,
    )

    # TODO: use this value to determine the number of channels
    max_number_of_points = Instrument.control(
        ":SYST:POIN:MAX?", ":SYST:POIN:MAX %d",
        """ An integer property that controls the maximum number of points the instrument can
        measure in a sweep. Note that when this value is changed, the instrument will be rebooted.
        Valid values are 25000 and 100000. When 25000 points is selected, the instrument supports 16
        channels with 16 traces each; when 100000 is selected, the instrument supports 1 channel
        with 16 traces.
        """,
        values=[25000, 100000],
        validator=strict_discrete_set,
        cast=int,
        check_get_errors=True,
        check_set_errors=True,
    )

    number_of_channels = Instrument.control(
        ":DISP:COUN?", ":DISP:COUN %d",
        """ An integer property that controls the number of displayed (and therefore accessible)
        channels. When the system is in 25000 points mode, the number of channels can be 1, 2, 3, 4,
        6, 8, 9, 10, 12, or 16; when the system is in 100000 points mode, the system only supports 1
        channel. If a value is provided that is not valid in the present mode, the instrument is set
        to the next higher channel number. Can be set.
        """,
        values=[1, 16],
        validator=strict_range,
        cast=int,
        check_get_errors=True,
        check_set_errors=True,
    )

    display_layout = Channel.control(
        ":DISP:SPL?", ":DISP:SPL %s",
        """ A string property that controls the channel display layout in a Row-by-Column format. 
        Can be set; valid values are: R1C1, R1C2, R2C1, R1C3, R3C1, R2C2C1, R2C1C2, C2R2R1, C2R1R2,
        R1C4, R4C1, R2C2, R2C3, R3C2, R2C4, R4C2, R3C3, R5C2, R2C5, R4C3, R3C4, R4C4. The number
        following the R indicates the number of rows, following the C the number of columns.
        """,
        values=["R1C1", "R1C2", "R2C1", "R1C3", "R3C1",
                "R2C2C1", "R2C1C2", "C2R2R1", "C2R1R2",
                "R1C4", "R4C1", "R2C2", "R2C3", "R3C2",
                "R2C4", "R4C2", "R3C3", "R5C2", "R2C5",
                "R4C3", "R3C4", "R4C4"],
        validator=strict_discrete_set,
        cast=int,
        check_get_errors=True,
        check_set_errors=True,
    )

    active_channel = Instrument.control(
        ":DISP:WIND:ACT?",":DISP:WIND%d:ACT",
        """ An integer property that controls the active channel. This property can be set.
        """,
        values=CHANNELS,
        validator=strict_range,
        cast=int,
        check_get_errors=True,
        check_set_errors=True,
    )

    trigger_source = Instrument.control(
        ":TRIG:SOUR?", ":TRIG:SOUR %s",
        """ A string property that controls the source of the sweep/measurement triggering. Can be 
        set; valid values are:

        =====   ==================================================
        value   description
        =====   ==================================================
        AUTO    Automatic triggering
        MAN     Manual triggering
        EXTT    Triggering from rear panel BNC via the GPIB parser
        EXT     External triggering port
        REM     Remote triggering
        =====   ==================================================
        """,
        values=["AUTO", "MAN", "EXTT", "EXT", "REM"],
        validator=strict_discrete_set,
        check_get_errors=True,
        check_set_errors=True,
    )

    external_trigger_type = Instrument.control(
        ":TRIG:EXT:TYP?", ":TRIG:EXT:TYP %s",
        """ A string property that controls the source of the sweep/measurement triggering. Can be
        set; valid values are POIN (for point), SWE (for sweep), CHAN (for channel), and ALL.
        """,
        values=["POIN", "SWE", "CHAN", "ALL"],
        validator=strict_discrete_set,
        check_get_errors=True,
        check_set_errors=True,
    )

    external_trigger_delay = Instrument.control(
        ":TRIG:EXT:DEL?", ":TRIG:EXT:DEL %g",
        """ A float property that controls the the delay time of the external trigger. Can be
        set; valid values are between 0 [s] and 10[s] in steps of 1e-9 [s] (i.e. 1 ns).
        """,
        values=[0, 10],
        validator=strict_range,
        check_get_errors=True,
        check_set_errors=True,
    )

    external_trigger_edge = Instrument.control(
        ":TRIG:EXT:EDG?", ":TRIG:EXT:EDG %s",
        """ A string property that controls the which edge is used for triggering of the external
        trigger. Can be set; valid values are POS (for positive or leading edge) or NEG (for
        negative or trailing edge).
        """,
        values=["POS", "NEG"],
        validator=strict_discrete_set,
        check_get_errors=True,
        check_set_errors=True,
    )

    external_trigger_handshake = Instrument.control(
        ":TRIG:EXT:HAND?", ":TRIG:EXT:HAND %s",
        """ A boolean property that controls status of the external trigger handshake. Can be set.
        """,
        values={True: 1, False: 0},
        map_values=True,
        check_get_errors=True,
        check_set_errors=True,
    )

    hold_function_all_channels = Instrument.control(
        ":SENS:HOLD:FUNC?", ":SENS:HOLD:FUNC %s",
        """ A string property that controls the hold function of all channels. Can be set; valid
        values are:

        =====   =================================================
        value   description
        =====   =================================================
        CONT    Perform continuous sweeps on all channels
        HOLD    Hold the sweep on all channels
        SING    Perform a single sweep and then hold all channels
        =====   =================================================
        """,
        values=["CONT", "HOLD", "SING"],
        validator=strict_discrete_set,
        check_get_errors=True,
        check_set_errors=True,
    )
