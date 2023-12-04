
import os
from pathlib import Path
from typing import Union, Tuple
import numpy as np

from pytektronix.pytektronix_base_classes import Scope, ScopeStateError, LoggedVXI11, LoggedVISA
from pytektronix.command_group_objects import Trigger, Channel, Horizontal, WaveformTransfer

# TODO: FIXME
class MDO3024:
    """The MDO3024 class is designed to control the Tektronix MDO3024 and perhaps other 3000
    Series tektronix oscilloscopes. This scope encapsulates most of the main requirements for the 
    oscilloscope, including Triggering (force and edge & more), horizontal controls, analog and digital
    channels, as well as waveform capture details.
    """

    def __init__(self, resource_id: str=None, vxi11: bool = False, strict: bool = True):
        """
            Parameters:
                - resource_id: The VISA name or the VXI11 ip address of the scope. Leave blank if unknow, and a connection wizard will be run.
                - vxi11: default False, set to true if connecting the the scope via VXI11 not VISA 
                - strict: default True, set to False if errors should be soft and not result in a raised exception.
        """

        self.instr = LoggedVISA(resource_id=resource_id) if not vxi11 else LoggedVXI11(IP=resource_id)

        self.trigger_accepted_values = {"mode":      ["normal", "auto"],
                                        "trig_type": ["edge", "logic", "pulse", "bus", "video"],
                                        "source":    [*[f"ch{i}" for i in range(1,5)], 
                                                      *[f"d{i}" for i in range(16)], 
                                                      "line", "rf"],
                                        "level":     ["ttl", "ecl", "any_number"]}
        self.trigger = Trigger(self.instr, self.trigger_accepted_values)

        self.horizontal_accepted_values = {"scale": [(4e-10, 1000)],
                                           "position": [(0, 100)]}
        self.horizontal = Horizontal(self.instr, self.horizontal_accepted_values)
        
        self.anlg_chan_accepted_values = {"position": [(-8.0, 8.0)],
                                          "offset": ["any_number"],
                                          "scale": [(1.0e-12, 500.0e12)],
                                          "coupling": ["ac", "dc", "dcreject"],
                                          "measurement_type": ["amplitude", "area", "burst",
                                                               "carea", "cmean", "crms", "delay", "fall",
                                                               "frequency", "high", "hits", "low", "max",
                                                               "mean", "median", "min", "nduty", "nedgecount",
                                                               "novershoot", "npulsecount", "nwidth", "peakhits",
                                                               "pedgecount", "pduty", "period", "phase", "pk2pk",
                                                               "povershoot", "ppulsecount", "pwidth", "rise", "rms",
                                                               "sigma1", "sigma2", "sigma3", "stdev", "tovershoot",
                                                               "waveforms"] }
        self.num_anlg_chans = 4
        self.num_digi_chans = 16
        self.ch_dict = {}

        for i in range(1, self.num_anlg_chans+1):
            self.ch_dict[f"ch{i}"] = Channel(i, self.instr, self.anlg_chan_accepted_values, strict=strict)
        for i in range(0, self.num_digi_chans):
            # TODO: FIXME THIS IS INCORRECT ACCEPTED VALUES
            self.ch_dict[f"d{i}"] = Channel(i, self.instr, self.anlg_chan_accepted_values, is_digital=True, strict=strict)
        
        #self.channels = (c for c in self.ch_dict.values)

        self.waveform_accepted_values = {"data_source": [*[f"ch{i}" for i in range(1,5)],
                                                         *[f"ref{i}" for i in range(1,5)],
                                                         *[f"d{i}" for i in range(0,16)],
                                                         "math", "rf_amplitude", "rf_frequency",
                                                         "rf_phase", "rf_normal", "rf_average",
                                                         "rf_maxhold", "rf_minhold"],
                                         "data_encoding": ["ascii", "fastest", "ribinary", 
                                                           "rpbinary", "sribinary", "srpbinary",
                                                           "fpbinary", "sfpbinary"],
                                         "data_start":  [(1, 2e6)],
                                         "data_stop": [(1, 2e6)],
                                         "num_points": [(1, 2e6)]}
        self.waveform = WaveformTransfer(self.instr, self.waveform_accepted_values)

        # TODO: allow data output to be list of bytes, floats, a csv or a estrace file
        self.data_output_type = None
        self.allowed_data_output_types = []

        # Function Remapping for simplicity
        self.make = self.instr.make
        self.model = self.instr.model

        self.write = self.instr.write
        self.ask = self.instr.ask
        self.read_raw = self.instr.read_raw
        self.close = self.instr.close

        self.write("HEADER 0")

    def default_setup(self):
        """Does exactly what pressing the 'Default Setup' or 'Auto Setup' button on the front
        panel of the oscilloscope would do
        """

        self.write("fpanel:press defaultsetup")
        self.write("HEADER 0")

    def compute_channel_offset_range(self, channel: Channel) -> Tuple:
        """ Internal function used to compute the accepted values of the 
            channel offset depending on probe resistance and the vertical scale. 

            Parameters:
                Channel: which channel to check the probe resistance of

            Returns:
                Tuple: (accepted values)
        """

        probe_res = {10e6: 0, 
                     50: 1}[float(self.ch_dict[channel].probe_resistance)]

        vdiv = self.scale

        mdo3024_ranges = [(1e-3, 50e-3), (50e-3,100e-3), 
                          (100e-3, 500e-3), (505e-3, 995e-3), 
                          (1, 5), (5, 10)]

        for idx, ran in enumerate(mdo3024_ranges):
            if vdiv > max(ran):
                continue
            accepted_values = [(-1, 1), (-.5, .5), 
                               (-10, 10), (-5, 5), 
                               (-100, 100), (-50, 50)][idx]
            if probe_res and max(accepted_values) > .5:
                accepted_values = (-5, 5)

        return accepted_values

    def set_trigger(self, mode: str=None, trig_type: str=None, 
                    source: str=None, level: Union[str, float]=None) -> None:
        """A scope method to set all trigger attributes desired.

            Parameters:
                - mode: desired trigger mode (normal, auto)
                - trig_type: desired trigger type (edge, logic, pulse, bus, video)
                - source: trigger source channel, any digital or logic channel allowed (ch<x> or d<x>)
                - level: desired level of the trigger in Volts, or (ttl, ecl)
        """

        if mode:
            self.trigger.mode = mode 
        if trig_type:
            self.trigger.trig_type = trig_type
        if source:
            self.trigger.source = source
        if level is not None:
            self.trigger.level = level

    #TODO: get individual settings
    def get_trigger_info(self, setting: str=None) -> str:
        """A getter to retreive and show all settings currently set for the trigger.
           returns a string of all info.

            Parameters:
                setting: No Effect as of now... #TODO - get individual settings
        """

        return f"Mode: {self.trigger.mode}\n\
               \rType: {self.trigger.trig_type}\n\
               \rSource: {self.trigger.source}\n\
               \rLevel: {self.trigger.level}"

    def set_horizontal(self, scale: float=None, position: float=None) -> None:
        """A scope method to set all horizontal attributes desired.

            Parameters:
                - scale: desired horizontal scale in Seconds, can be anything between (4e-10, 1000)
                - position: horizontal positioning expressed as a percentage of the screen (0, 100)
        """

        if scale is not None:
            self.horizontal.scale = scale
        if position is not None:
            self.horizontal.position = position

    def get_horizontal_info(self, setting: str=None) -> str:
        """A getter to retreive and show all settings currently set for the Horizontal.
           returns a string of all info.
        
            Parameters:
                setting: No Effect as of now... #TODO - get individual settings
        """

        return f"Scale: {self.horizontal.scale}\n \
                 \rPosition: {self.horizontal.position}"

    def set_channel(self, channel: str, position: float=None, offset: float=None, 
                    scale: float=None, coupling: str=None) -> None:
        """A scope method to set all channel attributes desired.

            Parameters:
                - channel: channel for which settings are being changed
                - position: horizontal position of channel referenced to centerline: between (-8,8)
                - offset: vertical offset of channel referenced to centeriline (any)
                - scale: vertical scale of the desired channel
                - coupling: specify coupling of a given channel (AC, DC, DCREJECT)
        """

        if channel not in self.ch_dict.keys():
            if self.strict:
                raise ValueError(f"No Channel '{channel}'. Must be one of {self.ch_dict.keys()}")
            print(f"No Channel '{channel}'. Must be one of {self.ch_dict.keys()}") 

        if position is not None:
            self.ch_dict[channel].position = position
        if offset is not None:
            self.ch_dict[channel].accepted_values["offset"] = [self.compute_channel_offset_range(self.ch_dict[channel])]
            self.ch_dict[channel].offset = offset
        if scale is not None:
            self.ch_dict[channel].scale = scale
        if coupling is not None:
            self.ch_dict[channel].coupling = coupling

    def get_channel_info(self, channel: str) -> str:
        """A getter to retreive and show all settings currently set for the Channel.
           returns a string of all info.
            
            Parameters:
                channel: a channel label (ch<x>, d<x>) of which to get info from
        """

        return f"{channel} Position: {self.ch_dict[channel].position}\n \
                 \r{channel} Offset: {self.ch_dict[channel].offset}\n \
                 \r{channel} scale: {self.ch_dict[channel].scale}\n \
                 \r{channel} coupling: {self.ch_dict[channel].scale}"

    def get_channel_measurement(self, channel: str, measure_type: str):
        """Gets the immediate value of measurement <measure_type> listed below
           from channel [ch1, ch2, ch3, ch4].
           - `amplitude`
           - `area | carea`
           - `burst`
           - `cmean | mean | median | stdev`
           - `crms | rms`
		   - `delay`
           - `frequency | period | phase`
		   - `high | low`
		   - `hits`
		   - `min | max`
		   - `peakhits`
           - `pedgecount | nedgecount`
		   - `pduty | nduty`
		   - `pk2pk`
           - `povershoot | novershoot | tovershoot`
		   - `ppulsecount | npulsecount`
		   - `pwidth | nwidth`
           - `rise | fall`
           - `sigma1 | sigma2 | sigma3`
           - `waveforms`
            """
        return self.ch_dict[channel].get_channel_measurement(measure_type)

    def set_digital(self) -> None:
        """A scope method to set all digital channel attributes"""

        raise NotImplementedError

    def set_waveform(self, data_source: str=None, data_encoding: str=None, 
                     data_width: int=None, data_start: int=None, 
                     data_stop: int=None) -> None:
        """A scope method to set all waveform data related attributes.

            Parameters:
                - data_source: source of waveform data (ch<x>, d<x>, ref<x>, math, rf_*)
                - data_encoding: data output encoding (ascii, fastest, ribinary, rpbinary, sribinary srpbinary, fpbinary, sfpbinary)
                - data_width: width of output data in bytes (1,2,4,8 - encoding dependant)
                - data_start: at which sample to start the data capture (1 to 2e6)
                - data_stop: at which sample to stop the data capture (1 to 2e6)
        """

        if data_source is not None:
            self.waveform.data_source = data_source 
        if data_encoding is not None: 
            self.waveform.data_encoding = data_encoding 
        if data_width is not None: 
            self.waveform.data_width = data_width
        if data_start is not None:
            self.waveform.data_start = data_start
        if data_stop is not None:
            self.waveform.data_stop = data_stop

    def get_waveform_info(self) -> str:
        """A getter to retreive and show all settings currently set for the waveform capture.
           returns a string of all info.
        """

        return f"Data Source: {self.waveform.data_source}\n \
                \rData Encoding: {self.waveform.data_encoding}\n \
                \rData Width (bytes): {self.waveform.data_width}\n \
                \rData Start (sample): {self.waveform.data_start}\n \
                \rData Stop (sample): {self.waveform.data_stop}"

    #TODO: Convert dat into useful for
    def get_waveform(self, format: str='default') -> Union[bytearray, np.ndarray, list]:
        """A scope method to caputure data from the scope returned as a bytearray, list, or np.ndarray.

            Parameters:
                - format: Specify return type as bytearray ('default'), list ('list') or numpy ndarray ('np_array')
        """

        data = self.waveform.get_data()
        dw = {1: np.uint8,
              2: np.uint16,
              4: np.uint32,
              8: np.uint64} 

        if not format or format == 'default':
            return data
        
        if format == "np_array":
            return np.frombuffer(data, dtype=dw[self.waveform.data_width])

        if format == "list":
            return list(np.frombuffer(data, dtype=dw[self.waveform.data_width]))
        

class MSO54:
    def __init__(self, resource_id: str=None, vxi11: bool = False, strict: bool = True):

        self.instr = LoggedVISA(resource_id=resource_id) if not vxi11 else LoggedVXI11(IP=resource_id)

        self.num_anlg_chans = 4
        self.num_digi_chans = 16

        self.triggerAAcceptedValues = {"mode":      ["normal", "auto"],
                                        "trig_type": ["edge", "logic", "width", 
                                                      "timeout", "runt", "window", 
                                                      "sethold", "transition", "bus"],
                                        "source":    [*[f"ch{i}" for i in range(1,self.num_anlg_chans+1)], 
                                                      *[f"ch{j}_d{i}" for j in range(1,self.num_anlg_chans + 1) for i in range(self.num_digi_chans)], 
                                                      "line", "aux"],
                                        "level":     ["ttl", "ecl", "any_number"]}
        self.trigger = Trigger(self.instr, self.triggerAAcceptedValues)
        self.triggerBAcceptedValues = {"mode":      ["normal", "auto"],
                                        "trig_type": ["edge", "logic", "pulse", "bus", "video"],
                                        "source":    [*[f"ch{i}" for i in range(1,5)], 
                                                      *[f"d{i}" for i in range(16)], 
                                                      "line", "rf"],
                                        "level":     ["ttl", "ecl", "any_number"]}
        self.triggerB = Trigger(self.instr, self.triggerBAcceptedValues, cn="trigger:b")

        self.horizontal_accepted_values = {"scale": [(4e-10, 1000)],
                                           "position": [(0, 100)]}
        self.horizontal = Horizontal(self.instr, self.horizontal_accepted_values)
        
        self.anlg_chan_accepted_values = {"position": ["any_number"],
                                          "offset": ["any_number"],
                                          "scale": ["any_number"],
                                          "coupling": ["ac", "dc", "dcreject"]}
        self.ch_dict = {}

        for i in range(1, self.num_anlg_chans+1):
            self.ch_dict[f"ch{i}"] = Channel(i, self.instr, self.anlg_chan_accepted_values, strict=strict)
            for j in range(0, self.num_digi_chans):
                self.ch_dict[f"ch_{i}_d{j}"] = Channel(j, self.instr, self.anlg_chan_accepted_values, is_digital=True, strict=strict, cn=f"ch{i}_d")
        
        #self.channels = (c for c in self.ch_dict.values)

        self.waveform_accepted_values = {"data_source": [*[f"ch{i}" for i in range(1,self.num_anlg_chans+1)],
                                                         *[f"ref{i}" for i in range(1,5)],
                                                         *[f"ch{j}_d{i}" for j in range(1, self.num_anlg_chans+1) for i in range(self.num_digi_chans)],
                                                         "math", "rf_amplitude", "rf_frequency",
                                                         "rf_phase", "rf_normal", "rf_average",
                                                         "rf_maxhold", "rf_minhold",
                                                         *[f"ch{i}_dall" for i in range(1,self.num_anlg_chans+1)],
                                                         "digitalall"],
                                         "data_encoding": ["ascii", "fastest", "ribinary", 
                                                           "rpbinary", "sribinary", "srpbinary",
                                                           "fpbinary", "sfpbinary"],
                                         "data_start":  [(1, 2e6)],
                                         "data_stop": [(1, 2e6)],
                                         "num_points": [(1, 2e6)]}
        self.waveform = WaveformTransfer(self.instr, self.waveform_accepted_values)

        # TODO: allow data output to be list of bytes, floats, a csv or a estrace file
        self.data_output_type = None
        self.allowed_data_output_types = []

        # Function Remapping for simplicity
        self.make = self.instr.make
        self.model = self.instr.model

        self.write = self.instr.write
        self.ask = self.instr.ask
        self.read_raw = self.instr.read_raw
        self.close = self.instr.close

        self.write("HEADER 0")

    def default_setup(self):
        self.write("fpanel:press defaultsetup")
        self.write("HEADER 0")

    def compute_channel_offset_range(self, channel: Channel) -> Tuple:
        probe_res = {10e6: 0, 
                     50: 1}[float(self.ch_dict[channel].probe_resistance)]

        vdiv = self.scale

        mdo3024_ranges = [(1e-3, 50e-3), (50e-3,100e-3), 
                          (100e-3, 500e-3), (505e-3, 995e-3), 
                          (1, 5), (5, 10)]

        for idx, ran in enumerate(mdo3024_ranges):
            if vdiv > max(ran):
                continue
            accepted_values = [(-1, 1), (-.5, .5), 
                               (-10, 10), (-5, 5), 
                               (-100, 100), (-50, 50)][idx]
            if probe_res and max(accepted_values) > .5:
                accepted_values = (-5, 5)

        return accepted_values

    def set_trigger(self, trigger: str="a", mode: str=None, trig_type: str=None, 
                    source: str=None, level: Union[str, float]=None) -> None:
        """A scope method to set all trigger attributes desired"""
        if mode:
            self.trigger.mode = mode
        if trig_type:
            self.trigger.trig_type = trig_type
        if source:
            self.trigger.source = source
        if level is not None:
            self.trigger.level = level

    def get_trigger_info(self, setting: str=None) -> str:
        #TODO: get individual settings
        return f"Mode: {self.trigger.mode}\n\
               \rType: {self.trigger.trig_type}\n\
               \rSource: {self.trigger.source}\n\
               \rLevel: {self.trigger.level}"
        
    def set_horizontal(self, scale: float=None, position: float=None) -> None:
        """A scope method to set all horizontal attributes desired"""
        if scale is not None:
            self.horizontal.scale = scale
        if position is not None:
            self.horizontal.position = position

    def get_horizontal_info(self, setting: str=None) -> str:
        return f"Scale: {self.horizontal.scale}\n \
                 \rPosition: {self.horizontal.position}"

    def set_channel(self, channel: str, position: float=None, offset: float=None, 
                    scale: float=None, coupling: str=None) -> None:
        """A scope method to set all channel attributes desired"""
        if channel not in self.ch_dict.keys():
            if self.strict:
                raise ValueError(f"No Channel '{channel}'. Must be one of {self.ch_dict.keys()}")
            print(f"No Channel '{channel}'. Must be one of {self.ch_dict.keys()}") 

        if position is not None:
            self.ch_dict[channel].position = position
        if offset is not None:
            self.ch_dict[channel].accepted_values["offset"] = [self.compute_channel_offset_range(self.ch_dict[channel])]
            self.ch_dict[channel].offset = offset
        if scale is not None:
            self.ch_dict[channel].scale = scale
        if coupling is not None:
            self.ch_dict[channel].coupling = coupling

    def get_channel_info(self, channel: str) -> str:
        return f"{channel} Position: {self.ch_dict[channel].position}\n \
                 \r{channel} Offset: {self.ch_dict[channel].offset}\n \
                 \r{channel} scale: {self.ch_dict[channel].scale}\n \
                 \r{channel} coupling: {self.ch_dict[channel].scale}"

    def set_digital(self) -> None:
        """A scope method to set all digital channel attributes"""
        raise NotImplementedError

    def set_waveform(self, data_source: str=None, data_encoding: str=None, 
                     data_width: int=None, data_start: int=None, 
                     data_stop: int=None) -> None:
        """A scope method to set all waveform data related attributes"""
        if data_source is not None:
            self.waveform.data_source = data_source 
        if data_encoding is not None: 
            self.waveform.data_encoding = data_encoding 
        if data_width is not None: 
            self.waveform.data_width = data_width
        if data_start is not None:
            self.waveform.data_start = data_start
        if data_stop is not None:
            self.waveform.data_stop = data_stop

    def get_waveform_info(self) -> str:
        return f"Data Source: {self.waveform.data_source}\n \
                \rData Encoding: {self.waveform.data_encoding}\n \
                \rData Width (bytes): {self.waveform.data_width}\n \
                \rData Start (sample): {self.waveform.data_start}\n \
                \rData Stop (sample): {self.waveform.data_stop}"

    #TODO: Convert dat into useful for
    def get_waveform(self, format: str='default') -> Union[bytearray, np.ndarray, list]:
        """A scope method to caputure data from the scope"""

        data = self.waveform.get_data()
        dw = {1: np.uint8,
              2: np.uint16,
              4: np.uint32,
              8: np.uint64} 

        if not format or format == 'default':
            return data
        
        if format == "np_array":
            return np.frombuffer(data, dtype=dw[self.waveform.data_width])

        if format == "list":
            return list(np.frombuffer(data, dtype=dw[self.waveform.data_width]))
 
if __name__ == "__main__":
    scope = MSO54()
    print(f"Make: {scope.instr.make}\nModel: {scope.instr.model}")
