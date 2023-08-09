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
    def __init__(self, instr: Scope, strict: bool=True, cn: str="trigger:a"):
        self.cn = cn
        self.instr = instr
        self.strict = strict
        self.supported_models = ["MDO3024", "DEBUG"]

    def force(self) -> None:
        """Checks if the scope is ready, and then forces a trigger event"""
        state = self.state
        if state != TrigStrings.READY.value:
            if self.strict:
                raise ScopeStateError(f"Trigger state '{state}' is not 'READY'")
            else:
                print(f"Scope in incorrect state to be forced: {check}")
                return
        allowed_values = {"MDO3024": ["force"]}
        self.instr.write("trigger force")
    
    def autoset(self)-> None:
        """Automatically set trigger level to 50% of range"""
        self.instr.write(f"{self.cn} setlevel") 

    @property
    def state(self):
        """Get current trigger STATE"""
        raw = self.instr.ask("trigger:state")
        return TrigStrings(raw.lower().strip()).value

    @property
    def mode(self):
        """Get current trigger MODE"""
        raw = self.instr.ask(f"{self.cn}:mode")
        return TrigStrings(raw.lower().strip()).value
    @mode.setter
    def mode(self, value: str):
        """Set trigger MODE"""
        accepted_values = {"MDO3024": ["normal", "auto"],
                           "DEBUG":   ["normal", "auto"]}
        self._set_property_accepted_vals(f"{self.cn}:mode", accepted_values, value) 

    @property
    def trig_type(self):
        """Get current trigger TYPE"""
        return TrigStrings(self.instr.ask(f"{self.cn}:type").lower().strip()).value
    # TODO: types
    @trig_type.setter
    def trig_type(self, value: str):
        """Set trigger TYPE"""
        accepted_values = {"MDO3024": ["edge", "logic", "pulse", "bus", "video"],
                           "DEBUG": ["edge", "logic"]}
        self._set_property_accepted_vals(f"{self.cn}:type", accepted_values, value)
    
    @property
    def source(self):
        """Get current trigger SOURCE"""
        trig_type = self.trig_type
        if self.trig_type not in "edge":
            raise NotImplementedError("Source can only be set when trig type is edge")
        return self.instr.ask(f"{self.cn}:{trig_type}:source").lower().strip()

    @source.setter
    def source(self, value):
        """Set trigger SOURCE"""
        trig_type = self.trig_type
        if self.trig_type not in ["edge"]:
            raise NotImplementedError("Source can only be set when trig type is edge")
        accepted_values = {"MDO3024": [*[f"ch{i}" for i in range(1,5)], 
                                       *[f"d{i}" for i in range(16)], 
                                       "line", "rf"],
                           "DEBUG":   ["CH1"]}
        self._set_property_accepted_vals(f"{self.cn}:{trig_type}:source", accepted_values, value)

    @property
    def level(self) -> float:
        """Get current trigger LEVEL"""
        trig_source = self.source 
        trig_source_type = trig_source.translate(str.maketrans('','',digits))
        accepted_values = {"MDO3024": ["aux", "ch", "d"],
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
                                  "DEBUG":   ["ch"]}
        if trig_source_type not in accepted_source_values[self.instr.model]:
            return "Trigger level cannot be ascertained for sources other that CH<i>, D<i>, or AUX"
        accepted_values = {"MDO3024": ["ttl", "ecl", "any_number"],
                           "DEBUG":   ["any_number"]}
        self._set_property_accepted_vals(f"{self.cn}:level:{trig_source}", accepted_values, value)


class Horizontal(CommandGroupObject):
    def __init__(self, instr: Scope, strict: bool=True, cn: str="horizontal"):
        self.cn = cn
        self.instr = instr
        self.strict = strict
        self.supported_models = ["MDO3024", "DEBUG"]
    
    @property
    def scale(self):
        """Get the current horizontal SCALE [S]"""
        return float(self.instr.ask(f"{self.cn}:scale"))
    @scale.setter
    def scale(self, value) -> float:
        """Specifies horizontal SCALE (400ps to 1000s).
           NOTE: Must be an exact scope scale increment (1, 4, 10 etc)"""
        accepted_values = {"MDO3024": [(4e-10, 1000)],
                           "DEBUG":   ["any_number"]}
        self._set_property_accepted_vals(f"{self.cn}:scale", accepted_values, value)

    @property
    def position(self) -> float:
        """Gets current horizontal POSITION"""
        return float(self.instr.ask(f"{self.cn}:position"))
    @position.setter
    def position(self, value):
        """Sets current horizontal POSITION as a percentage of the 
           currently captured waveform: [0%, 100%]"""
        accepted_values = {"MDO3024": [(0, 100)],
                           "DEBUG":   [(0, 100)]}
        self._set_property_accepted_vals(f"{self.cn}:position", accepted_values, value)
    
    @property
    def sample_rate(self):
        """Get the current horizontal SAMPLERATE"""
        return self.instr.ask(f"{self.cn}:samplerate")

class Channel(CommandGroupObject):
    def __init__(self, chan_num: int, instr: Scope, is_digital: bool=False,
                 strict: bool=True, cn: str="ch"):
        self.cn = f"{cn}{chan_num}"
        self.instr = instr
        self.is_digital = is_digital
        self.strict = strict
        self.supported_models = ["MDO3024", "DEBUG"]
    @property
    def position(self) -> float:
        """The position property."""
        return float(self.instr.ask(f"{self.cn}:position"))
    @position.setter
    def position(self, value):
        accepted_values = {"MDO3024": [(-8.0, 8.0)],
                           "DEBUG":   [(-8.0, 8.0)]}
        self._set_property_accepted_vals(f"{self.cn}:position", accepted_values, value)

    @property
    def offset(self) -> float:
        """The offset property."""
        return float(self.instr.ask(f"{self.cn}:offset"))
    @offset.setter
    def offset(self, value):
        #DONE: FIX offset accepted values - needs probe resistance
        accepted_values = {"MDO3024": None, 
                           "DEBUG":   ["any_number"]}

        accepted_values["MDO3024"] = self.compute_offset_range_for_mdo3024()

        self._set_property_accepted_vals(f"{self.cn}:offset", accepted_values, value)

    def compute_offset_range_for_mdo3024(self):
        probe_res = {10e6: 0, 
                     50: 1,
                     1e6: 0}[float(self.probe_resistance)]

        vdiv = self.scale

        mdo3024_ranges = [(1e-3, 50e-3), (50e-3,100e-3), 
                          (100e-3, 500e-3), (505e-3, 995e-3), 
                          (1, 5), (5, 10)]

        for idx, ran in enumerate(mdo3024_ranges):
            if vdiv > max(ran):
                continue
            accepted_values =[ [(-1, 1), (-.5, .5), 
                                (-10, 10), (-5, 5), 
                                (-100, 100), (-50, 50)][idx] ]
            if probe_res and max(accepted_values) > .5:
                accepted_values["MDO3024"] = [(-5, 5)]

        return accepted_values

    @property
    def scale(self) -> float:
        """The scale property."""
        return float(self.instr.ask(f"{self.cn}:scale"))
    @scale.setter
    def scale(self, value) -> None:
        """Sets the channel SCALE to <value> V/Division"""
        # TODO: FIX MDO3024 accepted scale range
        accepted_values = {"MDO3024": [(1.0e-12, 500.0e12)],
                           "DEBUG":   ["any_number"]} 
        self._set_property_accepted_vals(f"{self.cn}:scale", accepted_values, value)

    @property
    def probe_resistance(self) -> float:
        """Get channel PROBE RESISTANCE in OHMS"""
        return float(self.instr.ask(f"{self.cn}:probe:resistance"))

    @property
    def coupling(self):
        """The coupling property."""
        return self.instr.ask(f"{self.cn}:coupling")
    @coupling.setter
    def coupling(self, value):
        accepted_values = {"MDO3024": ["ac", "dc", "dcreject"]}
        self._set_property_accepted_vals(f"{self.cn}:coupling", accepted_values, value)

class WaveformTransfer(CommandGroupObject):
    def __init__(self, instr: Scope, strict: bool=False, auto_init=True):
        self.cn = "" 
        self.instr = instr
        self.strict = strict
        self.data_ready = False
        self.supported_models = ["MDO3024"]
        if auto_init:
            self.initialize_data()

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
        accepted_values = {"MDO3024": [*[f"ch{i}" for i in range(1,5)],
                                      *[f"ref{i}" for i in range(1,5)],
                                      *[f"d{i}" for i in range(0,16)],
                                      "math", "rf_amplitude", "rf_frequency",
                                      "rf_phase", "rf_normal", "rf_average",
                                      "rf_maxhold", "rf_minhold"],
                          "DEBUG": ["CH1"]} 
        self._set_property_accepted_vals("data:source", accepted_values, value)

    @property
    def data_encoding(self):
        """The data_encoding property."""
        return self.instr.ask("data:encdg")
    @data_encoding.setter
    def data_encoding(self, value):
        accepted_values = {"MDO3024": ["ascii", "fastest", "ribinary", 
                                       "rpbinary", "sribinary", "srpbinary",
                                       "fpbinary", "sfpbinary"],
                           "DEBUG": ["ascii", "binary"]}
        self._set_property_accepted_vals("data:encdg", accepted_values, value)

    @property
    def data_width(self) -> int:
        """The data_width property."""
        return int(self.instr.ask("data:width"))
    @data_width.setter
    def data_width(self, value):
        accepted_values = {"MDO3024": None}
        data_source = self.data_source
        value = str(value)
        if data_source == "digital":
            accepted_values["MDO3024"] = ["4", "8"]
        elif data_source in ["rf_normal", "rf_average", "rf_maxhold", "rf_minhold"]:
            accepted_values["MDO3024"] = ["4"]
        else:
            accepted_values["MDO3024"] = ["1", "2"]
        self._set_property_accepted_vals("data:width", accepted_values, value)

    @property
    def data_start(self) -> int:
        """The data_start property."""
        return int(self.instr.ask("data:start"))
    @data_start.setter
    def data_start(self, value):
        accepted_values = {"MDO3024": [(0, self.num_points)]}
        self._set_property_accepted_vals("data:start", accepted_values, value)

    @property
    def data_stop(self) -> int:
        """The data_stop property."""
        return int(self.instr.ask("data:stop"))
    @data_stop.setter
    def data_stop(self, value):
        accepted_values = {"MDO3024": [(1, self.num_points)]}
        self._set_property_accepted_vals("data:stop", accepted_values, value)

    @property
    def num_points(self) -> int:
        """The num_points property."""
        return int(self.instr.ask("WFMInpre:NR_Pt"))
    @num_points.setter
    def num_points(self, value):
        accepted_values = {"MDO3024": [(1, 2e6)]}
        raise NotImplementedError("setting num_points is not currently implemented")

    #TODO: fix read_raw when scope is VXI11 - breaks because read_raw not happy
    def get_data(self):
        if not self.data_ready:
            raise ScopeStateError("Scope is not ready to capture data... (Waveform Uninitialized??)")
        self.instr.write("curve?")

        if type(self.instr) == LoggedVXI11: 
            return self.instr.read()

        data = self.instr.read_raw() 
        return data

