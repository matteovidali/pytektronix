import pyvisa
import vxi11

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Union, Tuple
from abc import ABCMeta, abstractmethod
from string import digits
from aenum import MultiValueEnum

class Scope(metaclass=ABCMeta):
    """An abstract metaclass for any type of scope communication (VISA, VXI11 and DEBUG)""" 
    @abstractmethod
    def ask(self) -> str:
        """A method to query the scope, which expects a return string"""
        pass

    @abstractmethod
    def write(self) -> None:
        """A method to send a command to the scope without waiting for a response"""
        pass

class CommandGroupObject:
    """A command group meta object which all command group classes can inherit."""
    def _set_property_accepted_vals(self, prop: str, models_accepted_values: dict, value: any):
        if self.instr.model not in self.supported_models:
            raise NotImplementedError(f"Only models {','.join(self.supported_models)} currently supported")

        accepted_values = models_accepted_values[self.instr.model]
        
        if type(value) in [float, int]: 
            if "any_number" in accepted_values:
                pass
            elif any(isinstance(x, tuple) for x in accepted_values):
                accepted_range = [x for x in accepted_values if isinstance(x, tuple)][0]
                if not accepted_range and not isinstance(accepted_range, tuple):
                    raise ValueError("Range {accepted_range} is not accepted type")
                if value < min(accepted_range) or value > max(accepted_range):
                    raise ValueError(f"'{value}' is not in range {accepted_range}.")

        elif type(value) in [str]:
            if value.lower() not in accepted_values:
                raise ValueError(f"{value} is not an accepted trigger {prop}.\n", 
                                 f"Must be one of: ({','.join(accepted_values)})") 

        self.instr.write(f"{prop} {value}")

#TODO: FIX ME
class DebugScope(Scope):
    def __init__(self, loud: bool=False):
        self.make = "DEBUG_MAKE"
        self.model = "DEBUG"
        self.log = ""

        self.t_mode = "auto"
        self.t_type = "edge"
        self.t_source = "ch1"
        self.t_state = "ready"

        self.responses = {"trigger:state": self.t_state,
                          "trigger:a:mode": self.t_mode,
                          "trigger:a:type": self.t_type,
                          "trigger:a:edge:source": self.t_source}

    def ask(self, q: str):
    #return q+'?' if '?' not in q else q
        q += "?" if "?" not in q else ""
        self.log += q + "\n"
        return self.responses[q[:-1]] 

    def write(self, q:str):
        self.log += q + "\n"
        q = q.split(" ")
        if len(q) > 1:
            self.responses[q[0]] = q[1]
        return q


class LoggedVISA(Scope):
    def __init__(self, resource_id: str=None, loud: bool=False, log: bool=True):
        if not resource_id:
            self.visa = self._get_resource()
        else:
            try:
                self.visa = pyvisa.ResourceManager().open_resource(resource_id)
            except OSError:
                print("Resource Identifier '{resource_id}' is invalid...")
                self.visa = self._get_resource()

        self.loud = loud
        self.log_loud = log
        self.log_str: str = ""
        # TODO: Correct This:
        self.make, self.model = self.ask("*IDN?").split(",")[0:2]

    def _get_make_and_model(self):
        self.make, self.model = self.ask("*IDN?").split(",")[0:2]
        return self.make, self.model

    def _get_resource(self) -> pyvisa.Resource:
        """Gets a scope from the visa manager via command line options"""
        # Instantiate the Resource Manager and get the resources
        rm = pyvisa.ResourceManager()
        resources = rm.list_resources()

        # If there is only one resource, just get that
        if len(resources) <= 1:
            return rm.open_resource(resources[0])
    
        # Let user choose one of the resources
        print("Select a resource from the following list:")
        for idx, resource in enumerate(resources):
            print(f"{idx+1}: {resource}")
        
        res = input("\nType the number of the resource desired: ")
        
        # Fancy error checking - recursive (potential danger)
        try:
            return rm.open_resource(resources[int(res)])
        except ValueError:
            print(f"'{res}' is not a selectable resource.")
            print("Restarting...")
            return self._get_resource()
    
    def _check_instrument_errors(self, command: str = None, strict = False) -> Tuple[bool, str]:
        return False, "No Error" 

    def ask(self, q: str) -> str:
        """Sends a query string to the oscilloscope"""
        q = q + "?" if "?" not in q else q
        result = self.visa.query(q)
        err, err_str = self._check_instrument_errors(q)
        self.log(q, err, err_str)

        if self.loud:
            print(result, end='')

        return result
    
    def write(self, command: str) -> None: 
        """Writes a command string to the oscilloscope"""
        if self.loud:
            print(f"Writing Command '{command}'...")
        self.visa.write(command)
        err, err_str = self._check_instrument_errors(command)
        
        self.log(command, err, err_str)

    def read_raw(self):
        if self.loud:
            print("Reading Scope...")

        return self.visa._read_raw()

    def close(self):
        """Closes the visa connection"""
        self.visa.close()

    def log(self, value: str, err: bool=False, err_str: str=None) -> None:
        """Logs the commands sent to the scope, and notes if there was an error"""
        value += "\n" if "\n" not in value else value 
        if err:
            value = value+f" [FAILED - '{err_str}']"
        self.log_str += value


class LoggedVXI11(vxi11.Instrument, Scope):
    # TODO: Implement Loud VXI11
    def __init__(self, IP: str, loud: bool=False):
        super().__init__(IP)
        self.log: str = ""
        self.ip = IP if IP else os.environ["OSCILLOSCOPE"]

    def write(self, query: str):
        self.log += f"{query}\n"
        super().write(query)

    def ask(self, data: str):
        self.write(data)
        return super().read()
    
    def make_init(self, fpath: Path=None):
        fpath = self.ip+"_init.txt" if not fpath else fpath
        with open(fpath, "w+") as init_f:
            init_f.write(self.log)

    def close(self) -> None:
        raise NotImplementedError

class ScopeStateError(Exception):
    def __init__(self, message: str="INVALID SCOPE STATE"):
        super().__init__(message)

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
                     50: 1}[float(self.probe_resistance)]

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
    def data_width(self):
        """The data_width property."""
        return self.instr.ask("data:width")
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
    
    def get_data(self):
        if not self.data_ready:
            raise ScopeStateError("Scope is not ready to capture data... (Waveform Uninitialized??)")
        self.instr.write("curve?")
        return self.instr.read_raw()

# TODO: FIXME
class MDO3024:
    def __init__(self, resource_id: str=None, vxi11: bool = False, strict: bool = True):

        self.instr = LoggedVISA(resource_id=resource_id) if not vxi11 else LoggedVXI11(resource_id=resource_id)
        self.trigger = Trigger(self.instr)
        self.horizontal = Horizontal(self.instr)
        self.num_anlg_chans = 4
        self.num_digi_chans = 16
        self.ch_dict = {}

        for i in range(1, self.num_anlg_chans+1):
            self.ch_dict[f"ch{i}"] = Channel(i, self.instr, strict=strict)
        for i in range(0, self.num_digi_chans):
            self.ch_dict[f"d{i}"] = Channel(i, self.instr, is_digital=True, strict=strict)

        self.waveform = WaveformTransfer(self.instr)

        # TODO: allow data output to be list of bytes, floats, a csv or a estrace file
        self.data_output_type = None
        self.allowed_data_output_types = []

        self.make = self.instr.make
        self.model = self.instr.model

        self.write = self.instr.write
        self.ask = self.instr.ask
        self.read_raw = self.instr.read_raw

    def set_trigger(self, mode: str=None, trig_type: str=None, 
                    source: str=None, level: Union[str, float]=None):
        """A scope method to set all trigger attributes desired"""
        if mode:
            self.trigger.mode = mode 
        if trig_type:
            self.trigger.trig_type = trig_type
        if source:
            self.trigger.source = source
        if level is not None:
            print("SETTING LEVEL")
            self.trigger.level = level
        print(level)

    def set_horizontal(self, scale: float=None, position: float=None):
        """A scope method to set all horizontal attributes desired"""
        if scale is not None:
            self.horizontal.scale = scale
        if position is not None:
            self.horizontal.position = position

    def set_channel(self, channel: str, position: float=None, offset: float=None, 
                    scale: float=None):
        """A scope method to set all channel attributes desired"""
        if channel not in self.ch_dict.keys():
            if self.strict:
                raise ValueError(f"No Channel '{channel}'. Must be one of {self.ch_dict.keys()}")
            print(f"No Channel '{channel}'. Must be one of {self.ch_dict.keys()}") 

        if position is not None:
            self.ch_dict[channel].position = position
        if offset is not None:
            self.ch_dict[channel].offset = offset
        if scale is not None:
            self.ch_dict[channel].scale = scale

    def set_digital(self):
        """A scope method to set all digital channel attributes"""
        raise NotImplementedError

    def set_waveform(self, data_source: str=None, data_encoding: str=None, 
                     data_width: int=None):
        """A scope method to set all waveform data related attributes"""
        if data_source is not None:
            self.waveform.data_source = data_source
        if data_encoding is not None:
            self.waveform.data_encoding = data_encoding
        if data_width is not None:
            self.data_width = data_width

    #TODO: Convert dat into useful form
    def get_waveform(self):
        """A scope method to caputure data from the scope"""
        return self.waveform.get_data()


if __name__ == "__main__":
    scope = MDO3024()
    print(f"Make: {scope.instr.make}\nModel: {scope.instr.model}")
