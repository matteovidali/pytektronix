import sys
from pytektronix.scopes import MDO3024 
import pytest
from time import sleep

SCOPE = None
AV = None

@pytest.fixture(scope="session", autouse=True)
def setup_module():
    global SCOPE
    SCOPE = MDO3024()
    if not SCOPE:
        raise ScopeStateError("Please Connect a tektronix Scope to a VISA connection (USB, TCPIP, ETHERNET)")

    SCOPE.write("fpanel:press defaultsetup")
    while int(SCOPE.ask("BUSY")):
        continue
    SCOPE.write("fpanel:press menuoff")

def test_create():
    assert(SCOPE.make.lower() == "tektronix") 
    assert(SCOPE.model.lower() == "mdo3024")

def test_set_trigger_modes():
    SCOPE.set_trigger(mode="auto")
    assert(SCOPE.trigger.mode == "auto")

    SCOPE.set_trigger(mode="normal")
    assert(SCOPE.trigger.mode == "normal")

def test_set_trigger_types():
    trig_type_list = ["logic", "pulse", "bus", "video", "edge"]
    for trig_type in trig_type_list:
        SCOPE.set_trigger(trig_type=trig_type)
        assert(SCOPE.trigger.trig_type == trig_type)

def test_set_trigger_source():
    source_list = [*[f"ch{i}" for i in range(1,5)],
                   *[f"d{i}" for i in range(0,16)],
                   "line", "ch1"] 
    for source in source_list:
        SCOPE.set_trigger(source=source)
        assert(SCOPE.trigger.source == source)

def test_set_trigger_level():
    SCOPE.set_channel("ch1", scale=2)
    trig_levels = [1.4, 0.2, 0.24]
    for level in trig_levels:
        SCOPE.set_trigger(level=level)
        assert(SCOPE.trigger.level == level)

def test_sessionfinish():
    SCOPE.close()
