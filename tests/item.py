from openhab import Registry
from datetime import datetime, timedelta

from org.openhab.core.items import Item as Java_Item

import scope

try:
    item = Registry.getItem("TestItemBase")
except:
    config = {
        "name": "TestItemBase",
        "type": "Number"
    }
    item = Registry.addItem(config)

# Class type
assert isinstance(item, Java_Item)

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

# Check bool
test = item.getSemantic().isLocation()
assert isinstance(test, bool)
















