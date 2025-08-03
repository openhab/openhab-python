from openhab import Registry
import time

import scope

try:
    item = Registry.getItem("TestItemSwitch")
except:
    config = {
        "name": "TestItemSwitch",
        "type": "Switch"
    }
    item = Registry.addItem(config)

item.sendCommand("ON")
time.sleep(0.1)
assert item.getState() == scope.ON

item.sendCommand("OFF")
time.sleep(0.1)
assert item.getState() == scope.OFF

item.postUpdate(scope.ON)
time.sleep(0.1)
assert str(item.getState()) == "ON"

item.sendCommand(scope.OFF)
time.sleep(0.1)
assert str(item.getState()) == "OFF"
