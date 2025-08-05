import builtins

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

# Invalid parameter type
try:
    Registry.getItem(1)
except Exception as e:
    assert str(e) == "Unsupported parameter type <class 'int'>"
    assert builtins.__validateException__(e, __file__)

# Not found
try:
    Registry.getItem("CCCCCCCCC")
except Exception as e:
    assert str(e) == "Item CCCCCCCCC not found"
    assert builtins.__validateException__(e, __file__)

# Invalid parameter type
try:
    Registry.getItemState(1)
except Exception as e:
    assert str(e) == "Unsupported parameter type <class 'int'>"
    assert builtins.__validateException__(e, __file__)

# Not found
try:
    Registry.getItemState("CCCCCCCCC")
except Exception as e:
    assert str(e) == "Item state for CCCCCCCCC not found"
    assert builtins.__validateException__(e, __file__)


# Check bool
test = item.hasTag("1")
assert isinstance(test, bool)

# Check bool
test = item.getSemantic().isLocation()
assert isinstance(test, bool)

# Check missing function
try:
    item.test()
    assert False
except AttributeError as e:
    assert str(e) == "Java instance of 'org.openhab.core.library.items.NumberItem' has no attribute 'test'"
    assert builtins.__validateException__(e, __file__)

# Check wrong parameter
try:
    item.hasTag(1)
    assert False
except AttributeError as e:
    assert str(e) == "One of your function parameters does not match the required value type."
    assert builtins.__validateException__(e, __file__)

# Check "None" parameter
try:
    Registry.getItem("TestItemBase").getLastStateChange().test()
except AttributeError as e:
    assert str(e) == "None object has no attribute 'test'"
    assert builtins.__validateException__(e, __file__)

# Channel Java exception
try:
    item.link("xyz")
except AttributeError as e:
    assert str(e) == "java.lang.IllegalArgumentException: UID must have at least 4 segments: [xyz]"
    assert builtins.__validateException__(e, __file__)

# Channel not found
try:
    Registry.getChannel("astro:sun:a46403b2ed:rise1#start")
except Exception as e:
    assert str(e) == "Channel astro:sun:a46403b2ed:rise1#start not found"
    assert builtins.__validateException__(e, __file__)

# Thing Java exception
try:
    Registry.getThing("xyz")
except AttributeError as e:
    assert str(e) == "java.lang.IllegalArgumentException: UID must have at least 3 segments: [xyz]"
    assert builtins.__validateException__(e, __file__)

# Channel not found
try:
    Registry.getThing("a:b:c")
except Exception as e:
    assert str(e) == "Thing a:b:c not found"
    assert builtins.__validateException__(e, __file__)
