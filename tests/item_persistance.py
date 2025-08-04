from openhab import Registry
from datetime import datetime, timedelta

from org.openhab.core.items import Item as Java_Item

import scope

try:
    item = Registry.getItem("TestItemPersistance")
except:
    item = Registry.addItem("TestItemPersistance", "Number")

persistence = item.getPersistence()

# Check missing function
try:
    persistence.test(item)
    assert False
except AttributeError as e:
    assert str(e) == "Java instance of 'org.openhab.core.persistence.extensions.PersistenceExtensions' has no attribute 'test'"
    assert str(e.__traceback__.tb_frame.f_code.co_filename).endswith("item_persistance.py")

# Check wrong parameter
try:
    persistence.changedSince(item)
    assert False
except AttributeError as e:
    assert str(e) == "One of your function parameters does not match the required value type."
    assert str(e.__traceback__.tb_frame.f_code.co_filename).endswith("item_persistance.py")

# Check success
result = persistence.changedSince(datetime.now().astimezone())
assert result == False
persistence.changedSince(datetime.now())
assert result == False

# Check success
endDate = datetime.now()
startDate = endDate - timedelta(days=2)
persistence.getAllStatesBetween(startDate, endDate)

# Check bool
test = item.getSemantic().isLocation()
assert isinstance(test, bool)

