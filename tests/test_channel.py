import sys
sys.path.append("src/pytektronix")
from scopes import Channel, ScopeStateError, LoggedVISA
import pytest

SCOPE = None
AV = {"position": [(-8.0, 8.0)],
      "offset": ["any_number"],
      "scale": [(1.0e-12, 500.0e12)],
      "coupling": ["ac", "dc", "dcreject"]}

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

def test_init(TestScope) -> None:
    scope = TestScope
    chan = Channel(1, scope, AV)
    assert(chan.cn == "ch1")

def test_position(TestScope) -> None:
    scope = TestScope
    chan = Channel(1,  scope, AV)
    assert(chan.position == 0)
    
    chan.position = -2
    assert(chan.position == -2)
    
    with pytest.raises(ValueError):
        chan.position = 10

def test_offset(TestScope) -> None:
    scope = TestScope
    chan = Channel(1, scope, AV)
    
    assert(chan.offset == 0)
    
    chan.offset = 100e-3
    assert(chan.offset == 100e-3)

def test_scale(TestScope) -> None:
    scope = TestScope
    chan = Channel(1, scope, AV)
    assert(chan.scale == 1)

    chan.scale = 1.0e-2
    assert(chan.scale == 1e-2)

    chan.scale = 10
    assert(chan.scale == 10)

    with pytest.raises(ValueError):
        chan.scale = 10e14

def test_probe_resistance(TestScope) -> None:
    scope = TestScope
    chan = Channel(3, scope, AV)

    assert(type(chan.probe_resistance) == float)


def test_sessionfinish():
    global SCOPE
    SCOPE.close()
