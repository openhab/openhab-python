from openhab import Registry
from datetime import datetime

import scope

try:
    item = Registry.getItem("TestItemState")
except:
    config = {
        "name": "TestItemState",
        "type": "String"
    }
    item = Registry.addItem(config)

# Check success
state = item.getState()

# Check success
item.postUpdate(True)
item.postUpdate(1)
item.postUpdate(datetime.now())
item.postUpdate("test")
item.sendCommand(scope.ON)

#item.postUpdate(None)
