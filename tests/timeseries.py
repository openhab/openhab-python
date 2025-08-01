from openhab import Registry
from org.openhab.core.types import TimeSeries
from datetime import datetime

import scope

try:
    Registry.getItem("TestNumberItem")
except:
    config = {
        "name": "TestNumberItem",
        "type": "Number"
    }
    Registry.addItem(config)

# Test for different types of a State
ts = TimeSeries(TimeSeries.Policy.ADD)
ts.add(datetime.now(), "1.0")
ts.add(datetime.now(), scope.ON)
ts.add(datetime.now(), 1)
Registry.getItem("TestItem").getPersistence().persist(ts)
