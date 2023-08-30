import sys

from pytektronix.scopes import LoggedVISA
from pytektronix.command_group_objects import Trigger
from pytektronix.pytektronix_base_classes import ScopeStateError
import pytest
from time import sleep

SCOPE = None
AV = {"mode":      ["normal", "auto"],
      "trig_type": ["edge", "logic", "pulse", "bus", "video"],
      "source":    [*[f"ch{i}" for i in range(1,5)], 
                    *[f"d{i}" for i in range(16)], 
                    "line", "rf"],
      "level":     ["ttl", "ecl", "any_number"]}

@pytest.fixture()
def TestScope():
    global SCOPE
    return SCOPE

@pytest.fixture(scope="session", autouse=True)
def setup_module():
    global SCOPE
    SCOPE = LoggedVISA()
    if not SCOPE:
        raise ScopeStateError("Please Connect a tektronix Scope to a VISA connection (USB, TCPIP, ETHERNET)")

    SCOPE.write("fpanel:press defaultsetup")
    while int(SCOPE.ask("BUSY")):
        continue
    SCOPE.write("fpanel:press menuoff")

def test_trigger_create(TestScope) -> None:
    scope = TestScope
    trig = Trigger(scope, AV)
    assert(scope.model in trig.supported_models)

def test_trigger_create_unsupported_model(TestScope) -> None:
    scope = TestScope
    scope.model = "Unsupported Model"
    trig = Trigger(scope, AV)
    assert(scope.model not in trig.supported_models)
    scope._get_make_and_model()

def test_trigger_force(TestScope) -> None:
    scope = TestScope
    trig = Trigger(scope, AV)
    scope.write("fpanel:press singleseq")
    sleep(.5)
    trig.force()
    while int(scope.ask("BUSY")):
        sleep(.25)
    assert(trig.state == "save")

def test_trigger_force_not_ready(TestScope) -> None:
    scope = TestScope
    trig = Trigger(scope, AV)
    with pytest.raises(ScopeStateError):
        trig.force()

def test_trigger_autoset(TestScope) -> None:
    scope = TestScope
    trig = Trigger(scope, AV)
    trig.autoset()
    assert("trigger:a setlevel" in scope.log_str)

def test_state(TestScope) -> None:
    scope = TestScope
    trig = Trigger(scope, AV)
    trig.state
    assert("trigger:state" in scope.log_str)

def test_mode(TestScope) -> None:
    scope = TestScope
    trig = Trigger(scope, AV)
    a = trig.mode
    assert("trigger:a:mode?" in scope.log_str)

    trig.mode = "auto"
    assert(trig.mode == "auto")

    trig.mode = "normal"
    assert(trig.mode == "normal")

    with pytest.raises(ValueError):
        trig.mode = "Nonexistant Mode"

def test_type(TestScope) -> None:
    scope = TestScope
    trig = Trigger(scope, AV)
    a = trig.trig_type
    assert(a == "edge")
    assert("trigger:a:type?" in scope.log_str)

    trig.trig_type = "logic"
    assert(trig.trig_type == "logic")

    trig.trig_type = "edge"
    assert(trig.trig_type == "edge")
    
    with pytest.raises(ValueError):
        trig.trig_type = "Nonexistant Type"

def test_source(TestScope) -> None:
    scope = TestScope
    trig = Trigger(scope, AV)
    a = trig.source
    assert(a == "ch1")

    trig.source = "ch2"
    assert(trig.source == "ch2")

    assert("trigger:a:edge:source" in scope.log_str)
    
    with pytest.raises(ValueError):
        trig.source = "NonExistantChannel"

def test_level(TestScope) -> None:
    scope = TestScope
    trig = Trigger(scope, AV)
    a = trig.level
    assert(type(a) == float)

    trig.level = .5
    assert(trig.level == .5)
    
    with pytest.raises(ValueError):
        trig.level = "Unsupported"

def test_sessionfinish():
    SCOPE.close()
