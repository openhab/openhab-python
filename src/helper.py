import java
from polyglot import register_interop_type, ForeignNone

import time
import threading
import profile, pstats, io
from datetime import datetime, timedelta

import os
import traceback
from inspect import isfunction

import scope

from scope import RuleSupport, osgi#, RuleSimple

from openhab.jsr223 import TopCallStackFrame
from openhab.services import getService

from org.openhab.core.items import MetadataKey as Java_MetadataKey, Metadata as Java_Metadata

from org.openhab.core.thing import ChannelUID as Java_ChannelUID, ThingUID as Java_ThingUID
from org.openhab.core.automation.module.script.rulesupport.shared.simple import SimpleRule as Java_SimpleRule
from org.openhab.core.persistence.extensions import PersistenceExtensions as Java_PersistenceExtensions
from org.openhab.core.model.script.actions import Semantics as Java_Semantics

from org.openhab.core.items import Item as Java_Item, GroupItem as Java_GroupItem
from org.openhab.core.types import State as Java_State, PrimitiveType as Java_PrimitiveType, UnDefType as Java_UnDefType
from org.openhab.core.library.types import DecimalType as Java_DecimalType, UpDownType as Java_UpDownType, PercentType as Java_PercentType, DateTimeType as Java_DateTimeType

from org.openhab.core.persistence import HistoricItem as Java_HistoricItem

from org.openhab.core.items import ItemNotFoundException

from java.time import ZonedDateTime as Java_ZonedDateTime, Instant as Java_Instant
from java.lang import Object as Java_Object, Iterable as Java_Iterable

METADATA_REGISTRY = getService("org.openhab.core.items.MetadataRegistry")

ITEM_BUILDER_FACTORY = getService("org.openhab.core.items.ItemBuilderFactory")

ITEM_REGISTRY     = scope.itemRegistry
STATE_REGISTRY    = scope.items
THING_REGISTRY    = scope.things

EVENT_BUS         = scope.events

#scriptExtension   = scope.scriptExtension

AUTOMATION_MANAGER = RuleSupport.automationManager
LIFECYCLE_TRACKER = scope.lifecycleTracker

DYNAMIC_ITEM_TAG = "_DYNAMIC_"

# **** LOGGING ****
Java_LogFactory = java.type("org.slf4j.LoggerFactory")
LOG_PREFIX = "org.openhab.automation.pythonscripting"
NAME_PREFIX = ""
if 'javax.script.filename' in TopCallStackFrame:
    file_package = os.path.basename(TopCallStackFrame['javax.script.filename'])[:-3]
    LOG_PREFIX = "{}.{}".format(LOG_PREFIX, file_package)
    NAME_PREFIX = "{}".format(file_package)
elif 'ruleUID' in TopCallStackFrame:
    LOG_PREFIX = "{}.{}".format(LOG_PREFIX, TopCallStackFrame['ruleUID'])
    NAME_PREFIX = "{}".format(TopCallStackFrame['ruleUID'])
logger = Java_LogFactory.getLogger( LOG_PREFIX )
# *****************************************************************

class CustomForeignClass:
    def __str__(self):
        return str(self.getClass())

    def __getattr__(self, name):
        raise AttributeError("Java instance of '{}' has not attribute '{}'".format(self.getClass(), name))

register_interop_type(Java_Object, CustomForeignClass)

class NotInitialisedException(Exception):
    pass

def versiontuple(v):
    return tuple(map(int, (v.split("."))))

BUNDLE_VERSION = versiontuple(".".join(osgi.bundleContext.getBundle().getVersion().toString().split(".")[:3]))

class rule():
    def __init__(self, name=None, description=None, tags=None, triggers=None, conditions=None, profile=None):
        self.name = name
        self.description = description
        self.tags = tags
        self.triggers = triggers
        self.conditions = conditions
        self.profile = profile

    def __call__(self, clazz_or_function):
        proxy = self

        rule_isfunction = isfunction(clazz_or_function)
        rule_obj = clazz_or_function if rule_isfunction else clazz_or_function()

        clazz_or_function.logger = Java_LogFactory.getLogger( "{}.{}".format(LOG_PREFIX, clazz_or_function.__name__) )

        triggers = []
        if proxy.triggers is not None:
            triggers = proxy.triggers
        elif hasattr(rule_obj, "_when_triggers"):
            triggers = rule_obj._when_triggers
        elif hasattr(rule_obj, "buildTriggers") and callable(rule_obj.buildTriggers):
            triggers = rule_obj.buildTriggers()

        raw_triggers = []
        for trigger in triggers:
            raw_triggers.append(trigger.raw_trigger)

        conditions = []
        if proxy.conditions is not None:
            conditions = proxy.conditions
        elif hasattr(rule_obj, "_onlyif_conditions"):
            conditions = rule_obj._onlyif_conditions
        elif hasattr(rule_obj, "buildConditions") and callable(rule_obj.buildConditions):
            conditions = rule_obj.buildConditions()

        raw_conditions = []
        for condition in conditions:
            raw_conditions.append(condition.raw_condition)

        #register_interop_type(Java_SimpleRule, clazz)
        #subclass = type(clazz.__name__, (clazz, BaseSimpleRule,))

        # dummy helper to avoid "org.graalvm.polyglot.PolyglotException: java.lang.IllegalStateException: unknown type com.oracle.truffle.host.HostObject"
        class BaseSimpleRule(Java_SimpleRule):
            def execute(self, module, input):
                proxy.executeWrapper(rule_obj, rule_isfunction, module, input)

        base_rule_obj = BaseSimpleRule()

        name = "{}.{}".format(NAME_PREFIX, clazz_or_function.__name__) if proxy.name is None else proxy.name
        base_rule_obj.setName(name)

        if proxy.description is not None:
            base_rule_obj.setDescription(proxy.description)

        if proxy.tags is not None:
            base_rule_obj.setTags(proxy.tags)

        if len(raw_triggers) == 0:
            clazz_or_function.logger.warn("Rule '{}' has no triggers".format(name))
        else:
            base_rule_obj.setTriggers(raw_triggers)

            if len(raw_conditions) > 0:
                base_rule_obj.setConditions(raw_conditions)

            rule = AUTOMATION_MANAGER.addRule(base_rule_obj)

            if BUNDLE_VERSION < versiontuple("5.0.0"):
                actionConfiguration = rule.getActions().get(0).getConfiguration()
                actionConfiguration.put('type', 'application/x-python3')
                if '__file__' in TopCallStackFrame:
                    actionConfiguration.put('script', f"# text based rule in file: {TopCallStackFrame['__file__']}")
            else:
                rule.getConfiguration().put('sourceType', 'application/x-python3')
                if '__file__' in TopCallStackFrame:
                    rule.getConfiguration().put('source', f"# text based rule in file: {TopCallStackFrame['__file__']}")

            clazz_or_function.logger.info("Rule '{}' initialised".format(name))

        return rule_obj

    def appendEventDetailInfo(self, event):
        if event.getType().startswith("Item"):
            return " [Item: {}]".format(event.getItemName())
        elif event.getType().startswith("Group"):
            return " [Group: {}]".format(event.getItemName())
        elif event.getType().startswith("Thing"):
            return " [Thing: {}]".format(event.getThingUID())
        else:
            return " [Other: {}]".format(event.getType())

    def executeWrapper(self, rule_obj, rule_isfunction, module, input):
        try:
            start_time = time.perf_counter()

            # *** execute
            if self.profile:
                pr = profile.Profile()

                #self.logger.debug(str(getItem("Lights")))
                #pr.enable()
                if rule_isfunction:
                    pr.runctx('func(module, input)', {'module': module, 'input': input, 'func': rule_obj }, {})
                else:
                    pr.runctx('func(self, module, input)', {'self': rule_obj, 'module': module, 'input': input, 'func': rule_obj.execute }, {})
                status = None
            else:
                if rule_isfunction:
                    status = rule_obj(module, input)
                else:
                    status = rule_obj.execute(module, input)

            if self.profile:
                #pr.disable()
                s = io.StringIO()
                #http://www.jython.org/docs/library/profile.html#the-stats-class
                ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
                ps.print_stats()

                rule_obj.logger.info(s.getvalue())

            if status is None or status is True:
                elapsed_time = round( ( time.perf_counter() - start_time ) * 1000, 1 )

                try:
                    msg_details = self.appendEventDetailInfo(input['event'])
                except KeyError:
                    msg_details = ""

                msg = "Rule executed in " + "{:6.1f}".format(elapsed_time) + " ms" + msg_details

                rule_obj.logger.info(msg)

        except NotInitialisedException as e:
            rule_obj.logger.warn("Rule skipped: " + str(e) + " \n" + traceback.format_exc())
        except:
            rule_obj.logger.error("Rule execution failed:\n" + traceback.format_exc())

class JavaConversionHelper():
    @staticmethod
    def _convertZonedDateTime(zoned_date_time):
        return datetime.fromisoformat(zoned_date_time.toString().split("[")[0])

    @staticmethod
    def convertState(state):
        if java.instanceof(state, Java_DateTimeType):
            return JavaConversionHelper._convertZonedDateTime(state.getZonedDateTime())
        #elif state.getClass().getName() == 'org.openhab.core.library.types.QuantityType':
        #    return QuantityType(state)
        return state

    @staticmethod
    def convert(value):
        if java.instanceof(value, Java_Item):
            return Item(value)

        if java.instanceof(value, Java_State):
            return JavaConversionHelper.convertState(value)

        if java.instanceof(value, Java_ZonedDateTime):
            return JavaConversionHelper._convertZonedDateTime(value)

        if java.instanceof(value, Java_Instant):
            return datetime.fromisoformat(value.toString())

        if java.instanceof(value, Java_HistoricItem):
            return HistoricItem(value)

        if java.instanceof(value, Java_Iterable):
            _values = []
            for _value in value:
                _values.append(JavaConversionHelper.convert(_value))
            return _values

        # convert polyglot.ForeignNone => None
        if isinstance(value, ForeignNone):
            return None

        return value

class ItemPersistence():
    def __init__(self, item, service_id = None):
        self.item = item
        self.service_id = service_id

    def getStableMinMaxState(self, time_slot, end_time = None):
        current_end_time = datetime.now().astimezone() if end_time is None else end_time
        min_time = current_end_time - timedelta(seconds=time_slot)

        min_value = None
        max_value = None

        value = 0.0
        duration = 0

        entry = self.persistedState(current_end_time)

        while True:
            currentStartTime = entry.getTimestamp()

            if currentStartTime < min_time:
                currentStartTime = min_time

            _duration = ( currentStartTime - current_end_time ).total_seconds()
            _value = entry.getState().doubleValue()

            if min_value == None or min_value > _value:
                min_value = _value

            if max_value == None or max_value < _value:
                max_value = _value

            duration = duration + _duration
            value = value + ( _value * _duration )

            current_end_time = currentStartTime - timedelta(microseconds=1)

            if current_end_time < min_time:
                break

            entry = self.persistedState(current_end_time)

        value = ( value / duration )

        return [ Java_DecimalType(value), Java_DecimalType(min_value), Java_DecimalType(max_value) ]

    def getStableState(self, time_slot, end_time = None):
        value, _, _ = self.getStableMinMaxState(time_slot, end_time)
        return value

    def __getattr__(self, name):
        attr = getattr(Java_PersistenceExtensions, name)
        if callable(attr):
            return lambda *args, **kwargs: JavaConversionHelper.convert( attr(*(tuple([self.item.raw_item]) + args + tuple([] if self.service_id is None else [self.service_id]) )) )
        return attr

class ItemSemantic():
    def __init__(self, item):
        self.item = item

    def __getattr__(self, name):
        attr = getattr(Java_Semantics, name)
        if callable(attr):
            return lambda *args, **kwargs: JavaConversionHelper.convert( attr(*(tuple([self.item.raw_item]) + args)) )
        return attr

class HistoricItem():
    def __init__(self, raw_historic_item):
        self.raw_historic_item = raw_historic_item

    def __getattr__(self, name):
        attr = getattr(self.raw_historic_item, name)
        if callable(attr):
            return lambda *args, **kwargs: JavaConversionHelper.convert( attr(*args) )
        return attr

class Item():
    def __init__(self, raw_item):
        self.raw_item = raw_item

    def postUpdate(self, state):
        if isinstance(state, datetime):
            state = state.isoformat()
        EVENT_BUS.postUpdate(self.raw_item, Item._toOpenhabPrimitiveType(state))

    def postUpdateIfDifferent(self, state):
        if not Item._checkIfDifferent(self.getState(), state):
            return False

        self.postUpdate(state)
        return True

    def sendCommand(self, command):
        EVENT_BUS.sendCommand(self.raw_item, Item._toOpenhabPrimitiveType(command))

    def sendCommandIfDifferent(self, command):
        if not Item._checkIfDifferent(self.getState(), command):
            return False

        self.sendCommand(command)

        return True

    def getPersistence(self, service_id = None):
        return ItemPersistence(self, service_id)

    def getSemantic(self):
        return ItemSemantic(self)

    def __getattr__(self, name):
        attr = getattr(self.raw_item, name)
        if callable(attr):
            return lambda *args, **kwargs: JavaConversionHelper.convert( attr(*args) )
        return attr

    @staticmethod
    # Insight came from openhab-js. Helper function to convert a JS type to a primitive type accepted by openHAB Core, which often is a string representation of the type.
    #
    # Converting any complex type to a primitive type is required to avoid multi-threading issues (as GraalJS does not allow multithreaded access to a script's context),
    # e.g. when passing objects to persistence, which then persists asynchronously.
    def _toOpenhabPrimitiveType(value):
        if value is None:
            return 'NULL'
        if java.instanceof(value, Java_UnDefType):
            return 'UNDEF'
        if isinstance(value, str) or isinstance(value, int) or isinstance(value, float):
            return value
        if isinstance(value, datetime):
            return value
        return value.toFullString()

    @staticmethod
    def _checkIfDifferent(current_state, new_state):
        if not java.instanceof(current_state, Java_UnDefType):
            if java.instanceof(current_state, Java_PercentType):
                if isinstance(new_state, str):
                    if new_state == "UP":
                        new_state = 0
                    if new_state == "DOWN":
                        new_state = 100
                elif java.instanceof(new_state, Java_UpDownType):
                    new_state = (0 if new_state.toFullString() == "UP" else 100)

            if java.instanceof(new_state, Java_PrimitiveType):
                new_state = new_state.toFullString()
            elif isinstance(new_state, datetime):
                new_state = new_state.isoformat()
            else:
                new_state = str(new_state)

            if java.instanceof(current_state, Java_PrimitiveType):
                current_state = current_state.toFullString()
            elif isinstance(current_state, datetime):
                current_state = current_state.isoformat()
            else:
                current_state = str(current_state)

            return current_state != new_state
        return True

class Thing():
    def __init__(self, raw_item):
        self.raw_item = raw_item

    def __getattr__(self, name):
        return getattr(self.raw_item, name)

class Channel():
    def __init__(self, raw_item):
        self.raw_item = raw_item

    def __getattr__(self, name):
        return getattr(self.raw_item, name)

class Registry():
    @staticmethod
    def getThings():
        return THING_REGISTRY.getAll()

    @staticmethod
    def getThing(uid):
        thing = THING_REGISTRY.get(Java_ThingUID(uid))
        if thing is None:
            raise NotInitialisedException("Thing {} not found".format(uid))
        return Thing(thing)

    @staticmethod
    def getChannel(uid):
        channel = THING_REGISTRY.getChannel(Java_ChannelUID(uid))
        if channel is None:
            raise NotInitialisedException("Channel {} not found".format(uid))
        return Channel(channel)

    @staticmethod
    def getItemMetadata(item_or_item_name, namespace):
        item_name = Registry._getItemName(item_or_item_name)
        return METADATA_REGISTRY.get(Java_MetadataKey(namespace, item_name))

    @staticmethod
    def setItemMetadata(item_or_item_name, namespace, value, configuration=None):
        item_name = Registry._getItemName(item_or_item_name)
        if Registry.getItemMetadata(item_or_item_name, namespace) == None:
            return METADATA_REGISTRY.add(Java_Metadata(Java_MetadataKey(namespace, item_name), value, configuration))
        else:
            return METADATA_REGISTRY.update(Java_Metadata(Java_MetadataKey(namespace, item_name), value, configuration))

    @staticmethod
    def removeItemMetadata(item_or_item_name, namespace = None):
        item_name = Registry._getItemName(item_or_item_name)
        if namespace == None:
            METADATA_REGISTRY.removeItemMetadata(item_name)
            return None
        else:
            return METADATA_REGISTRY.remove(Java_MetadataKey(namespace, item_name))

    @staticmethod
    def getItemState(item_name, default = None):
        if isinstance(item_name, str):
            state = STATE_REGISTRY.get(item_name)
            if state is None:
                raise NotInitialisedException("Item state for {} not found".format(item_name))
            if default is not None and java.instanceof(state, Java_UnDefType):
                state = default
            return JavaConversionHelper.convertState(state)
        raise Exception("Unsupported parameter type {}".format(type(item_name)))

    @staticmethod
    def getItem(item_name):
        if isinstance(item_name, str):
            try:
                return Item(ITEM_REGISTRY.getItem(item_name))
            except ItemNotFoundException:
                raise NotInitialisedException("Item {} not found".format(item_name))
        raise Exception("Unsupported parameter type {}".format(type(item_name)))

    @staticmethod
    def resolveItem(item_or_item_name):
        if isinstance(item_or_item_name, Item):
            return item_or_item_name
        return Registry.getItem(item_or_item_name)

    @staticmethod
    def addItem(item_config):
        item = Registry._createItem(item_config)
        ITEM_REGISTRY.add(item.raw_item)

        return Registry.getItem(item_config['name'])

    @staticmethod
    def safeItemName(s):
        # Remove quotes and replace non-alphanumeric with underscores
        return ''.join([c if c.isalnum() else '_' for c in s.replace('"', '').replace("'", '')])

    @staticmethod
    def _createItem(item_config):
        if 'name' not in item_config or 'type' not in item_config:
            raise Exception('item_config.name or item_config.type not set')

        item_config['name'] = Registry.safeItemName(item_config['name'])

        base_item = None
        if item_config['type'] == 'Group' and 'giBaseType' in item_config:
            base_item = ITEM_BUILDER_FACTORY.newItemBuilder(item_config['giBaseType'], item_config['name'] + '_baseItem').build()
        if item_config['type'] != 'Group':
            item_config['groupFunction'] = None

        if 'tags' not in item_config:
            item_config['tags'] = []
        item_config['tags'].append(DYNAMIC_ITEM_TAG)

        try:
            builder = ITEM_BUILDER_FACTORY.newItemBuilder(item_config['type'], item_config['name']) \
                .withCategory(item_config.get('category')) \
                .withLabel(item_config.get('label')) \
                .withTags(item_config['tags'])

            if 'groups' in item_config:
                builder = builder.withGroups(item_config['groups'])

            if base_item is not None:
                builder = builder.withBaseItem(base_item)
            if item_config.get('groupFunction') is not None:
                builder = builder.withGroupFunction(item_config['groupFunction'])

            item = builder.build()
            return Item(item)
        except Exception as e:
            logger.error('Failed to create Item: {}'.format(e))
            raise

    @staticmethod
    def _getItemName(item_or_item_name):
        if isinstance(item_or_item_name, str):
            return item_or_item_name
        elif isinstance(item_or_item_name, Item):
            return item_or_item_name.getName()
        raise Exception("Unsupported parameter type {}".format(type(item_or_item_name)))


# Timer will not work in transformations scripts, because LIFECYLE_TRACKER cleanup will never run successfully
class Timer(threading.Timer):
    # could also be solved by storing it in a private cache => https://next.openhab.org/docs/configuration/jsr223.html
    # because Timer & ScheduledFuture are canceled when a private cache is cleaned on unload or refresh
    activeTimer = []

    @staticmethod
    def _clean():
        for timer in list(Timer.activeTimer):
            timer.cancel()
            timer.join(5)

    @staticmethod
    def createTimeout(duration, callback, args=[], kwargs={}, old_timer = None, max_count = 0 ):
        if old_timer != None:
            old_timer.cancel()
            max_count = old_timer.max_count

        max_count = max_count - 1

        if max_count == 0:
            callback(*args, **kwargs)

            return None

        timer = Timer(duration, callback, args, kwargs )
        timer.start()
        timer.max_count = max_count

        return timer

    def __init__(self, duration, callback, args=[], kwargs={}):
        super().__init__(duration, self.handler, [args, kwargs])
        self.callback = callback

    def handler(self, args=[], kwargs={}):
        try:
            self.callback(*args, **kwargs)
            try:
                Timer.activeTimer.remove(self)
            except ValueError:
                # can happen when timer is executed and canceled at the same time
                # could be solved with a LOCK, but this solution is more efficient, because it works without a LOCK
                pass
        except:
            logger.error("{}".format(traceback.format_exc()))
            raise

    def start(self):
        if self.is_alive():
            return
        #log.info("timer started")
        Timer.activeTimer.append(self)
        super().start()

    def cancel(self):
        if not self.is_alive():
            return
        Timer.activeTimer.remove(self)
        super().cancel()

LIFECYCLE_TRACKER.addDisposeHook(Timer._clean)
