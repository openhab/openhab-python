from openhab import Registry
from datetime import datetime

from org.openhab.core.items import Item as Java_Item

import scope

try:
    Registry.getItem("TestNumberItem")
except:
    config = {
        "name": "TestNumberItem",
        "type": "Number"
    }
    Registry.addItem(config)

# Class type
item = Registry.getItem("TestNumberItem")
assert isinstance(item, Java_Item)

# Check success
item.postUpdate(datetime.now())
item.sendCommand(scope.ON)

# Check bool
test = item.hasTag("1")
assert isinstance(test, bool)

# Check wrong parameter
try:
    item.hasTag(1)
    assert False
except AttributeError:
    pass

# Check wrong parameter
try:
    item.getPersistence().changedSince(item)
    assert False
except AttributeError:
    pass

# Check success
item.getPersistence().changedSince(datetime.now().astimezone())
item.getPersistence().changedSince(datetime.now())

# Check bool
test = item.getSemantic().isLocation()
assert isinstance(test, bool)
















