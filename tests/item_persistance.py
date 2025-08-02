from openhab import Registry
from datetime import datetime, timedelta

from org.openhab.core.items import Item as Java_Item

import scope

try:
    item = Registry.getItem("TestItemPersistance")
except:
    config = {
        "name": "TestItemPersistance",
        "type": "Number"
    }
    item = Registry.addItem(config)

persistence = item.getPersistence()
# Check wrong parameter
try:
    persistence.changedSince(item)
    assert False
except AttributeError as e:
    assert str(e) == "One of your function parameters does not match the required value type."
    assert str(e.__traceback__.tb_frame.f_code.co_filename).endswith("item_persistance.py")

# Check success
persistence.changedSince(datetime.now().astimezone())
persistence.changedSince(datetime.now())

# Check success
endDate = datetime.now()
startDate = endDate - timedelta(days=2)
persistence.getAllStatesBetween(startDate, endDate)

# Check bool
test = item.getSemantic().isLocation()
assert isinstance(test, bool)
