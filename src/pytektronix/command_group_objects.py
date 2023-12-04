from aenum import MultiValueEnum
from pytektronix.pytektronix_base_classes import CommandGroupObject, Scope
from pytektronix.pytektronix_base_classes import ScopeStateError, LoggedVXI11

from string import digits

class TrigStrings(MultiValueEnum):
    READY = "ready", "rea"
    SAVE = "save", "sav"
    TRIGGERED = "triggered", "trig" 
    ARMED = "armed", "arm"
    EDGE = "edge", "edg"
    LOGIC = "logic", "logi"
    PULSE = "pulse", "puls"
    BUS = "bus"
    VIDEO = "video", "vid"
    NORMAL = "normal", "norm"
    AUTO = "auto"

class Trigger(CommandGroupObject):
    def __init__(self, instr: Scope, accepted_values: dict, strict: bool=True, cn: str="trigger:a"):
        self.cn = cn
        self.instr = instr
        self.strict = strict
        self._accepted_values = accepted_values

    @property
    def accepted_values(self):
        """The accepted_values property."""
        return self._accepted_values
    @accepted_values.setter
    def accepted_values(self, value):
        self._accepted_values = value

    def force(self) -> None:
        """Checks if the scope is ready, and then forces a trigger event"""
        state = self.state
        if state != TrigStrings.READY.value:
            if self.strict:
                raise ScopeStateError(f"Trigger state '{state}' is not 'READY'")
            else:
                print(f"Scope in incorrect state to be forced: {check}")
                return

        self.instr.write("trigger force")
    
    def autoset(self)-> None:
        """Automatically set trigger level to 50% of range"""
        self.instr.write(f"{self.cn} setlevel") 

    @property
    def state(self):
        """Get current trigger STATE"""
        raw = self.instr.ask("trigger:state")
        return TrigStrings(raw.lower()).value

    @property
    def mode(self):
        """Get current trigger MODE"""
        raw = self.instr.ask(f"{self.cn}:mode")
        return TrigStrings(raw.lower()).value
    @mode.setter
    def mode(self, value: str):
        """Set trigger MODE"""
        self._global_setter("mode",f"{self.cn}:mode", value)

    @property
    def trig_type(self):
        """Get current trigger TYPE"""
        return TrigStrings(self.instr.ask(f"{self.cn}:type").lower()).value
    # TODO: types
    @trig_type.setter
    def trig_type(self, value: str):
        """Set trigger TYPE"""
        self._global_setter("trig_type", f"{self.cn}:type", value)
    
    @property
    def source(self):
        """Get current trigger SOURCE"""
        trig_type = self.trig_type
        if self.trig_type not in "edge":
            raise NotImplementedError("Source can only be set when trig type is edge")
        return self.instr.ask(f"{self.cn}:{trig_type}:source").lower()

    @source.setter
    def source(self, value):
        """Set trigger SOURCE"""
        trig_type = self.trig_type
        if trig_type not in ["edge"]:
            raise NotImplementedError("Source can only be set when trig type is edge")
        
        self._global_setter("source", f"{self.cn}:{trig_type}:source", value)

    @property
    def level(self) -> float:
        """Get current trigger LEVEL"""
        trig_source = self.source 
        trig_source_type = trig_source.translate(str.maketrans('','',digits))
        accepted_values = {"MDO3024": ["aux", "ch", "d"],
                           "MSO54": ["aux", "ch", "d"], 
                           "DEBUG":   ["ch"]}
        if trig_source_type not in accepted_values[self.instr.model]:
            return "Trigger level cannot be ascertained for sources other that CH<i>, D<i>, or AUX"
        raw = self.instr.ask(f"{self.cn}:level:{trig_source}")
        return float(raw)
    @level.setter
    def level(self, value):
        """Set trigger LEVEL"""
        trig_source = self.source 
        trig_source_type = trig_source.translate(str.maketrans('','',digits))
        accepted_source_values = {"MDO3024": ["aux", "ch", "d"],
                                  "MSO54": ["aux", "ch", "ch_d"], 
                                  "DEBUG":   ["ch"]}
        if trig_source_type not in accepted_source_values[self.instr.model]:
            return "Trigger level cannot be ascertained for sources other that CH<i>, D<i>, or AUX"
        self._global_setter("level", f"{self.cn}:level:{trig_source}", value)


class Horizontal(CommandGroupObject):
    def __init__(self, instr: Scope, accepted_values: dict, strict: bool=True, cn: str="horizontal"):
        self.cn = cn
        self.instr = instr
        self.strict = strict    
        self._accepted_values = accepted_values
   
    @property
    def accepted_values(self):
        """The accepted_values property."""
        return self._accepted_values
    @accepted_values.setter
    def accepted_values(self, value):
        self._accepted_values = value

    @property
    def scale(self):
        """Get the current horizontal SCALE [S]"""
        return float(self.instr.ask(f"{self.cn}:scale"))
    @scale.setter
    def scale(self, value) -> float:
        """Specifies horizontal SCALE (400ps to 1000s).
           NOTE: Must be an exact scope scale increment (1, 4, 10 etc)"""
        self._global_setter("scale", f"{self.cn}:scale", value)

    @property
    def position(self) -> float:
        """Gets current horizontal POSITION"""
        return float(self.instr.ask(f"{self.cn}:position"))
    @position.setter
    def position(self, value):
        """Sets current horizontal POSITION as a percentage of the 
           currently captured waveform: [0%, 100%]"""
        self._global_setter("position", f"{self.cn}:position", value)
    
    @property
    def sample_rate(self):
        """Get the current horizontal SAMPLERATE"""
        return self.instr.ask(f"{self.cn}:samplerate")

class Channel(CommandGroupObject):
    def __init__(self, chan_num: int, instr: Scope, accepted_values: dict, 
                 is_digital: bool=False, strict: bool=True, cn: str="ch"):
        self.cn = f"{cn}{chan_num}"
        self.instr = instr
        self.is_digital = is_digital
        self.strict = strict
        self._accepted_values = accepted_values

    @property
    def accepted_values(self):
        """The accepted_values property."""
        return self._accepted_values
    @accepted_values.setter
    def accepted_values(self, value):
        self._accepted_values = value

    @property
    def position(self) -> float:
        """The position property."""
        if self.is_digital:
            raise ScopeNotSupportedError("Digital Channels have no position property")
        return float(self.instr.ask(f"{self.cn}:position"))
    @position.setter
    def position(self, value):
        if self.is_digital:
            raise ScopeNotSupportedError("Digital Channels have no position property")
        self._global_setter("position", f"{self.cn}:position", value)

    @property
    def offset(self) -> float:
        """The offset property."""
        if self.is_digital:
            raise ScopeNotSupportedError("Digital Channels have no offset property")
        return float(self.instr.ask(f"{self.cn}:offset"))
    @offset.setter
    def offset(self, value):
        """Set the channel offset"""
        if self.is_digital:
            raise ScopeNotSupportedError("Digital Channels have no offset property")
        self._global_setter("offset", f"{self.cn}:offset", value)

    @property
    def scale(self) -> float:
        """The scale property."""
        if self.is_digital:
            raise ScopeNotSupportedError("Digital Channels have no scale property")
        return float(self.instr.ask(f"{self.cn}:scale"))
    @scale.setter
    def scale(self, value) -> None:
        """Sets the channel SCALE to <value> V/Division"""
        if self.is_digital:
            raise ScopeNotSupportedError("Digital Channels have no scale property")
        # TODO: FIX MDO3024 accepted scale range
        self._global_setter("scale", f"{self.cn}:scale", value)

    @property
    def probe_resistance(self) -> float:
        """Get channel PROBE RESISTANCE in OHMS"""
        if self.is_digital:
            raise ScopeNotSupportedError("Digital Channels have no probe resistance property")
        return float(self.instr.ask(f"{self.cn}:probe:resistance"))

    @property
    def coupling(self):
        """The coupling property."""
        if self.is_digital:
            raise ScopeNotSupportedError("Digital Channels have no coupling property")
        return self.instr.ask(f"{self.cn}:coupling")
    @coupling.setter
    def coupling(self, value):
        if self.is_digital:
            raise ScopeNotSupportedError("Digital Channels have no position property")
        self._global_setter("coupling", f"{self.cn}:coupling", value)

    def get_measurement(self, desired_measure):
        self._global_setter("measurement_source", f"measurement:immed:source1 {self.cn}")
        self._global_setter("measurement_type", "measurement:immed:type", desired_measure)
        return self.instr.ask(":measurement:immed:value")


class WFStrings(MultiValueEnum):
    ASCII = 'ascii', 'asc'
    FASTEST = 'fastest'
    RIBINARY = 'ribinary', 'rib'
    RPBINARY = 'rpbinary', 'rpb'
    SRIBINARY = 'sribinary', 'sri'
    SRPBINARY = 'srpbinary', 'srp'
    FPBINARY = 'fpbinary', 'fpb'
    SFPBINARY = 'sfpbinary', 'sfp'

class WaveformTransfer(CommandGroupObject):
    def __init__(self, instr: Scope, accepted_values: dict, 
                 strict: bool=False, auto_init=True):
        self.cn = "" 
        self.instr = instr
        self.strict = strict
        self.data_ready = False
        self._accepted_values = accepted_values
        if auto_init:
            self.initialize_data()

    @property
    def accepted_values(self):
        """The accepted_values property."""
        return self._accepted_values
    @accepted_values.setter
    def accepted_values(self, value):
        self._accepted_values = value

    def initialize_data(self, data_source: str = "CH1"):
        self.data_source = "CH1"
        self.data_encoding = "fastest"
        self.data_width = 1
        self.data_ready = True

    def get_data_preamble(self):
        if not self.data_ready:
            raise ScopeStateError("Scope is not initialized to send data." \
                                  "Please initialize the waveform transfer" \
                                  "structure (WaveformTransfer.initialize_data())")
        return self.instr.ask("wfmoutpre")

    @property
    def data_source(self):
        """The data_source property."""
        return self.instr.ask("data:source")
    @data_source.setter
    def data_source(self, value):
        #TODO: Fix allowed types!
        self._global_setter("data_source", "data:source", value)

    @property
    def data_encoding(self):
        """The data_encoding property."""
        return WFStrings(self.instr.ask("data:encdg").lower()).value
    @data_encoding.setter
    def data_encoding(self, value):
        self._global_setter("data_encoding", "data:encdg", value)

    @property
    def data_width(self) -> int:
        """The data_width property."""
        return int(self.instr.ask("data:width"))
    @data_width.setter
    def data_width(self, value):
        #TODO: re-think accepted value calculation here
        data_source = self.data_source
        value = str(value)
        if data_source == "digital":
            self.accepted_values["data_width"] = ["4", "8"]
        elif data_source in ["rf_normal", "rf_average", "rf_maxhold", "rf_minhold"]:
            self.accepted_values["data_width"] = ["4"]
        else:
            self.accepted_values["data_width"] = ["1", "2"]
        self._global_setter("data_width","data:width", value)

    @property
    def data_start(self) -> int:
        """The data_start property."""
        return int(self.instr.ask("data:start"))
    @data_start.setter
    def data_start(self, value):
        self._global_setter("data_start", "data:start", value)

    @property
    def data_stop(self) -> int:
        """The data_stop property."""
        return int(self.instr.ask("data:stop"))
    @data_stop.setter
    def data_stop(self, value):
        self._global_setter("data_stop", "data:stop", value)

    @property
    def num_points(self) -> int:
        """The num_points property."""
        return int(self.instr.ask("WFMInpre:NR_Pt"))
    @num_points.setter
    def num_points(self, value):
        raise NotImplementedError("setting num_points is not currently implemented")

    #TODO: fix read_raw when scope is VXI11 - breaks because read_raw not happy
    def get_data(self) -> bytearray:
        if not self.data_ready:
            raise ScopeStateError("Scope is not ready to capture data... (Waveform Uninitialized??)")

        
        de = self.data_encoding.lower()
        data = None

        self.instr.write("curve?")

        if type(self.instr) == LoggedVXI11: 
            data =  self.instr.read()
        else:
            data = self.instr.read_raw() 
             
        if ('binary' or 'fastest') in de:
            # Removes #N<ndigits> header from binary encoding
            # data[1] contains the N of <n-digits>
            # the char and int cast turn it fome an ascii byte into an integer
            # the 2 is there because the 0th index of the bytearray contains '
            # and the 1th index of the bytearray is the N iteslf.
            data = data[2 + int(chr(data[1])):] 

        return data

    #class MStrings(MultiValueEnum):
    #    TEST = 'test', 'test'
    #
    #class Measure(CommandGroupObject):
    #    def __init__(self, instr: Scope, accepted_values: dict,
    #                 strict: bool=False):
    #        self.instr = instr
    #        self.strict = strict
    #        self._accepted_values = accepted_values
    #        self.active_measurements = {}
    #
    #    @property
    #    def accepted_values(self):
    #        return self._accepted_values
    #
    #    @accepted_values.setter
    #    def accepted_values(self, value):
    #        return self._accepted_values = value
    #
    #    @property
    #    def measurement_parameters(self):
    #        """The 'Measurement?' property."""
    #        return self.instr.ask(f"measurement")
    #
    #    @property
    #    def immediate(self):
    #        """The immediate property."""
    #        return self.instr.ask(f"measurement:immed")
    #    
    #    @property
    #    def immediate_source(self):
    #        return self.instr.ask("measurement:immed:source") 
    #    @immediate_source.setter
    #    def immediate_source(self, value):
    #        return _global_setter("immediate_source", "measurement:immed:source", value)
    #
    #    @property
    #    def measurement(self):
    #        """The measurement property."""
    #        return self._measurement
    #    @measurement.setter
    #    def measurement(self, value):
    #        self._measurement = value
    #
    #    @property
    #    def measurement_type(self):
    #        """The measurement_type property."""
    #        return self._measurement_type
    #    @measurement_type.setter
    #    def measurement_type(self, value):
    #        self._measurement_type = value 
    #
    #    def which_measurements_active(self):
    #        return self.active_measurements.keys()
    #
    #    def get_measurement_value(self, measurement:str):
    #        x = self.active_measurements[measurement]
    #        return self.instr.ask(f"measurement:meas{x}:value")
    #    
    #    def activate_measurement(self, type:str, position: int=None):
    #        pass
