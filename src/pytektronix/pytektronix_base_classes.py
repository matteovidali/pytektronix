import pyvisa
import vxi11
from typing import Tuple
from pathlib import Path
from abc import ABCMeta, abstractmethod, abstractproperty

class ScopeStateError(Exception):
    """An Error type for when the scopes current state is not correct for a 
       given command. 
       Examples include when forcing a trigger, the scope trigger
       state must be 'READY', and if the scopes are in 'strict' mode, and a
       trigger force is invoked, pytektronix will raise a ScopeStateError.
       If the 'strict' mode is disabled with (...strict=False) optional, then
       a simple warning will be printed instead, and the 'force' command will
       not be executed."""
    def __init__(self, message: str="INVALID SCOPE STATE"):
        super().__init__(message)

class ScopeNotSupportedError(Exception):
    """An Error type to demonstrate when a setting has no scope support"""
    def __init__(self, message: str="NO SCOPE SUPPORT"):
        super().__init__(message)

class Scope(metaclass=ABCMeta):
    """An abstract metaclass for any type of scope communication 
      (VISA, VXI11,  DEBUG, etc.)""" 
    @abstractmethod
    def ask(self) -> str:
        """An ask method to query the scope which expects to return a string \
           (lowercase) must be included in any scope class"""
        pass

    @abstractmethod
    def write(self) -> None:
        """A method to send a command to the scope without waiting for a 
           response"""
        pass

class CommandGroupObject(metaclass=ABCMeta):
    """A command group meta object which all command group classes can inherit."""

    @property
    def supported_models(self):
        return ["MSO54", "MDO3024", "DEBUG"]

    @abstractproperty
    def accepted_values(self):
        pass

    def _global_setter(self, command_name: str, command: str, value):
        """Global call for setting"""
        if command_name not in self.accepted_values.keys():
            raise KeyError(f"No accepted value present for '{command_name.upper()}' - please set an accepted value parameter for '{command_name}'") 
        av = self.accepted_values[command_name]
        self._set_property_accepted_vals(command, av, value)
            
    def _set_property_accepted_vals(self, prop: str, models_accepted_values: dict, value: any):
        if self.instr.model not in self.supported_models:
            raise NotImplementedError(f"MODEL== {self.instr.model} - Only models {','.join(self.supported_models)} currently supported")

        accepted_values = models_accepted_values #models_accepted_values[self.instr.model]
        
        if not value:
            self.instr.write(f"{prop}")
        elif type(value) in [float, int]: 
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
        
        res = int(input("\nType the number of the resource desired: "))
        
        # Fancy error checking - recursive (potential danger)
        try:
            return rm.open_resource(resources[int(res-1)])
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

        return result.strip()
    
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

        return self.visa._read_raw().strip()

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
        self.make, self.model = self._get_make_and_model()

    def _get_make_and_model(self):
        self.make, self.model = self.ask("*IDN?").split(",")[0:2]
        return self.make, self.model

    def write(self, query: str):
        self.log += f"{query}\n"
        super().write(query)

    def ask(self, q: str):
        q = q + "?" if "?" not in q else q
        self.write(q)
        return super().read()

    def make_init(self, fpath: Path=None):
        fpath = self.ip+"_init.txt" if not fpath else fpath
        with open(fpath, "w+") as init_f:
            init_f.write(self.log)

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

