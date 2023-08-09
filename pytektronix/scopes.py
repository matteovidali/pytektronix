
import os
from pathlib import Path
from typing import Union, Tuple

from pytektronix.pytektronix_base_classes import Scope, ScopeStateError, LoggedVXI11, LoggedVISA
from pytektronix.command_group_objects import Trigger, Channel, Horizontal, WaveformTransfer

# TODO: FIXME
class MDO3024:
    def __init__(self, resource_id: str=None, vxi11: bool = False, strict: bool = True):

        self.instr = LoggedVISA(resource_id=resource_id) if not vxi11 else LoggedVXI11(IP=resource_id)
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

    def set_trigger(self, mode: str=None, trig_type: str=None, 
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
    def get_waveform(self, format: str='default'):
        """A scope method to caputure data from the scope"""
        if not format or format == 'default':
            return self.waveform.get_data()

class MSO54:
     def __init__(self, resource_id: str=None, vxi11: bool = False, strict: bool = True):

        self.instr = LoggedVISA(resource_id=resource_id) if not vxi11 else LoggedVXI11(IP=resource_id)
        self.trigger_A = Trigger(self.instr)
        self.trigger_B = Trigger(self.instr, cn="trigger:b")
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

        # Function Remapping for simplicity
        self.make = self.instr.make
        self.model = self.instr.model

        self.write = self.instr.write
        self.ask = self.instr.ask
        self.read_raw = self.instr.read_raw
        self.close = self.instr.close

        self.write("HEADER 0")



if __name__ == "__main__":
    scope = MDO3024()
    print(f"Make: {scope.instr.make}\nModel: {scope.instr.model}")
