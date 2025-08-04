from openhab import Registry
from datetime import datetime, timedelta

from org.openhab.core.items import Item as Java_Item

import time

try:
    item = Registry.getItem("TestItemDatetime")
except:
    item = Registry.addItem("TestItemDatetime", "Number")

item.sendCommand(1)
time.sleep(0.1)

value1 = datetime.now().astimezone()
value2 = item.getLastStateUpdate()
assert isinstance(value2,datetime)

assert isinstance(value1 - value2,timedelta)

assert (value1 == value2) == False
assert (value1 < value2) == False
assert (value1 > value2) == True
