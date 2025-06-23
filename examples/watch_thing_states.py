from openhab import rule, logger, Registry
from openhab.triggers import when, onlyif, GenericEventTrigger
from openhab.helper import NotInitialisedException

from scope import ON, OFF

def setThingItemStatus(thinguid, status):
    thing = Registry.getThing(thinguid)
    logger.info("Thing {} is now {}".format(thing.getLabel(), status))

    item_name = Registry.safeItemName(thing.getLabel()) + "_status"
    try:
        logger.info("Looking for Item {}".format(item_name))
        item = Registry.getItem(item_name)
    except NotInitialisedException as e:
        logger.info("Creating Item {} not found in registry".format(item_name))
        itemConfig = {
            "name": item_name,
            "type": "String",
            "label": "Status of {}".format(thing.getLabel()),
            "groups": ['Things_Status']
        }
        item = Registry.addItem(itemConfig)
    item.sendCommand(status)

@rule("Set Things Status")
@when("system started")
def set_things_status(module, input):
    things = Registry.getThings()
    for thing in things:
        setThingItemStatus(thing.getUID(), thing.getStatus().toString())

@rule("Things Status Switch")
@when("Item Things_Status changed")
def ThingsStatusSwitchRule(module, input):
    event = input['event']
    offlineItems = event.getItemState().intValue()
    logger.info("There are {} offline Things".format(offlineItems))
    Registry.getItem("Things_Offline_Switch").sendCommand("ON" if offlineItems > 0 else "OFF")

@rule(
    name = "Watch thing states",
    triggers = [ GenericEventTrigger("", "ThingStatusInfoChangedEvent", "openhab/things/**") ]
)
def ThingStatusChangedRule(module, input):
    event = input['event']
    setThingItemStatus(event.getThingUID(), event.getStatusInfo().toString())
