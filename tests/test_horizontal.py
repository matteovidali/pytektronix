import sys
from pytektronix.scopes import LoggedVISA, Horizontal, ScopeStateError
import pytest

SCOPE = None
AV = {"scale": [(4e-10, 1000)],
      "position": [(0, 100)]}

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
    hor = Horizontal(scope, AV)
    a = hor.scale
    assert(a == 4e-6)

def test_scale(TestScope) -> None:
    scope = TestScope
    hor = Horizontal(scope, AV)

    a = hor.scale
    assert(a == 4.0e-6)

    hor.scale = 1
    assert(hor.scale == 1)

def test_position(TestScope) -> None:
    scope = TestScope
    hor = Horizontal(scope, AV)
    
    a = hor.position
    assert(a == 50)

def test_sessionfinish() -> None:
    global SCOPE
    SCOPE.close()

