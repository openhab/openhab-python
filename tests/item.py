from openhab import Registry
from datetime import datetime, timedelta

from org.openhab.core.items import Item as Java_Item

import scope

try:
    item = Registry.getItem("TestItemBase")
except:
    item = Registry.addItem("TestItemBase", "Number")

# Class type
assert isinstance(item, Java_Item)

# Check bool
test = item.hasTag("1")
assert isinstance(test, bool)

# Check missing function
try:
    item.test()
    assert False
except AttributeError as e:
    assert str(e) == "Java instance of 'org.openhab.core.library.items.NumberItem' has no attribute 'test'"
    assert str(e.__traceback__.tb_frame.f_code.co_filename).endswith("item.py")

# Check wrong parameter
try:
    item.hasTag(1)
    assert False
except AttributeError as e:
    assert str(e) == "One of your function parameters does not match the required value type."
    assert str(e.__traceback__.tb_frame.f_code.co_filename).endswith("item.py")

# Check "None" parameter
try:
    Registry.getItem("TestItemBase").getLastStateChange().test()
except AttributeError as e:
    assert str(e) == "None object has no attribute 'test'"
    assert str(e.__traceback__.tb_frame.f_code.co_filename).endswith("item.py")

try:
    item.link("xyz")
except AttributeError as e:
    assert str(e) == "java.lang.IllegalArgumentException: UID must have at least 4 segments: [xyz]"
    assert str(e.__traceback__.tb_frame.f_code.co_filename).endswith("item.py")


# Check bool
test = item.getSemantic().isLocation()
assert isinstance(test, bool)


































