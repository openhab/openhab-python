from polyglot import ForeignNone, ForeignObject, interop_type

import java
import os
import time
import threading
import traceback
import profile, pstats, io
from inspect import isfunction
from datetime import datetime, timezone, timedelta

from openhab.jsr223 import TopCallStackFrame
from openhab.services import getService

from org.openhab.core.thing import ChannelUID as Java_ChannelUID, ThingUID as Java_ThingUID
from org.openhab.core.automation.module.script.rulesupport.shared.simple import SimpleRule as Java_SimpleRule
from org.openhab.core.persistence.extensions import PersistenceExtensions as Java_PersistenceExtensions
from org.openhab.core.model.script.actions import Semantics as Java_Semantics

from org.openhab.core.items import Item as Java_Item, MetadataKey as Java_MetadataKey, Metadata as Java_Metadata, ItemNotFoundException
from org.openhab.core.types import PrimitiveType as Java_PrimitiveType, UnDefType as Java_UnDefType
from org.openhab.core.library.types import DecimalType as Java_DecimalType, UpDownType as Java_UpDownType, PercentType as Java_PercentType, DateTimeType as Java_DateTimeType

from java.time import ZonedDateTime as Java_ZonedDateTime, Instant as Java_Instant
from java.lang import Object as Java_Object, Iterable as Java_Iterable

from scope import RuleSupport, osgi#, RuleSimple
import scope

METADATA_REGISTRY = getService("org.openhab.core.items.MetadataRegistry")
ITEM_BUILDER_FACTORY = getService("org.openhab.core.items.ItemBuilderFactory")

def versiontuple(v):
    return tuple(map(int, (v.split("."))))
BUNDLE_VERSION = versiontuple(".".join(osgi.bundleContext.getBundle().getVersion().toString().split(".")[:3]))

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

class NotInitialisedException(Exception):
    pass

class rule():
    def __init__(self, name=None, description=None, tags=None, triggers=None, conditions=None, runtime_measurement=True, profile_code=False):
        self.name = name
        self.description = description
        self.tags = tags
        self.triggers = triggers
        self.conditions = conditions
        self.runtime_measurement = runtime_measurement
        self.profile_code = profile_code

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

        name = "{}.{}".format(NAME_PREFIX, clazz_or_function.__name__) if proxy.name is None else proxy.name

        base_rule_obj = BaseSimpleRule()
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

            rule = RuleSupport.automationManager.addRule(base_rule_obj)

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

    def executeWrapper(self, rule_obj, rule_isfunction, module, input):
        try:
            start_time = time.perf_counter()

            if self.profile_code:
                pr = profile.Profile()
                pr.runctx('func(module, input)', {'module': module, 'input': input, 'func': rule_obj if rule_isfunction else rule_obj.execute }, {})
                s = io.StringIO()
                ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
                ps.print_stats()
                rule_obj.logger.info(s.getvalue())
            else:
                rule_obj(module, input) if rule_isfunction else rule_obj.execute(module, input)

            if self.runtime_measurement:
                try:
                    if input['event'].getType().startswith("Item"):
                        msg_details = " [Item: {}]".format(input['event'].getItemName())
                    elif input['event'].getType().startswith("Group"):
                        msg_details = " [Group: {}]".format(input['event'].getItemName())
                    elif input['event'].getType().startswith("Thing"):
                        msg_details = " [Thing: {}]".format(input['event'].getThingUID())
                    else:
                        msg_details = " [Other: {}]".format(input['event'].getType())
                except KeyError:
                    msg_details = ""
                rule_obj.logger.info("Rule executed in " + "{:6.1f}".format(round( ( time.perf_counter() - start_time ) * 1000, 1 )) + " ms" + msg_details)

        except NotInitialisedException as e:
            rule_obj.logger.warn("Rule skipped: " + str(e) + " \n" + traceback.format_exc())
        except:
            rule_obj.logger.error("Rule execution failed:\n" + traceback.format_exc())

@interop_type(Java_Instant)
class Instant(datetime):
    def __new__(cls, year, month=None, day=None, hour=0, minute=0, second=0,
                microsecond=0, tzinfo=None, *, fold=0):
        return datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second, microsecond=microsecond, tzinfo=tzinfo, fold=fold)

    def __getattribute__(self, name):
        #print(name)
        match name:
            case "_year": return super().getYear()
            case "_month": return super().getMonthValue()
            case "_day": return super().getDayOfMonth()
            case "_hour": return super().getHour()
            case "_minute": return super().getMinute()
            case "_second": return super().getSecond()
            case "_microsecond": return int(super().getNano() / 1000)
            case "_tzinfo": return None
            case "_hashcode": return -1
            case "_fold": return 0
        return super().__getattribute__(name)

    def __hash__(self):
        return hash(self._getstate())

@interop_type(Java_ZonedDateTime)
class DateTime(Instant):
    def __getattribute__(self, name):
        match name:
            case "_tzinfo": return timezone(timedelta(seconds=super().getOffset().getTotalSeconds()), super().getZone().getId())
        return super().__getattribute__(name)

@interop_type(Java_Item)
class Item():
    def postUpdate(self, state):
        scope.events.postUpdate(self, state)

    def postUpdateIfDifferent(self, state):
        if not Item._checkIfDifferent(self.getState(), state):
            return False
        self.postUpdate(state)
        return True

    def sendCommand(self, command):
        scope.events.sendCommand(self, command)

    def sendCommandIfDifferent(self, command):
        if not Item._checkIfDifferent(self.getState(), command):
            return False
        self.sendCommand(command)
        return True

    def getPersistence(self, service_id = None):
        return ItemPersistence(self, service_id)

    def getSemantic(self):
        return ItemSemantic(self)

    def getMetadata(self):
        return ItemMetadata(self)

    @staticmethod
    def buildSafeName(s):
        # Remove quotes and replace non-alphanumeric with underscores
        return ''.join([c if c.isalnum() else '_' for c in s.replace('"', '').replace("'", '')])

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

class ItemSemantic(traceback.__CustomProxyClass__):
    def __init__(self, item):
        super().__init__(Java_Semantics, lambda *args: tuple([item]) + args)

class ItemPersistence(traceback.__CustomProxyClass__):
    def __init__(self, item, service_id = None):
        super().__init__(Java_PersistenceExtensions, lambda *args: tuple([item]) + args + tuple([] if service_id is None else [service_id]) )

    def getStableMinMaxState(self, time_slot, end_time = None):
        current_end_time = datetime.now().astimezone() if end_time is None else end_time
        min_time = current_end_time - timedelta(seconds=time_slot)

        min_value = max_value = None
        value = duration = 0.0

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

        return [ Java_DecimalType(value / duration), Java_DecimalType(min_value), Java_DecimalType(max_value) ]

    def getStableState(self, time_slot, end_time = None):
        value, _, _ = self.getStableMinMaxState(time_slot, end_time)
        return value

class ItemMetadata():
    def __init__(self, item):
        self.item = item

    def get(self, namespace):
        return METADATA_REGISTRY.get(Java_MetadataKey(namespace, self.item.getName()))

    def set(self, namespace, value, configuration=None):
        if self.get(namespace) == None:
            return METADATA_REGISTRY.add(Java_Metadata(Java_MetadataKey(namespace, self.item.getName()), value, configuration))
        else:
            return METADATA_REGISTRY.update(Java_Metadata(Java_MetadataKey(namespace, self.item.getName()), value, configuration))

    def remove(self, namespace):
        return METADATA_REGISTRY.remove(Java_MetadataKey(namespace, self.getName()))

    def removeAll(self):
        METADATA_REGISTRY.removeItemMetadata(self.getName())

class Registry():
    @staticmethod
    def getThings():
        return scope.things.getAll()

    @staticmethod
    def getThing(uid):
        thing = scope.things.get(Java_ThingUID(uid))
        if thing is None:
            raise NotInitialisedException("Thing {} not found".format(uid))
        return thing

    @staticmethod
    def getChannel(uid):
        channel = scope.things.getChannel(Java_ChannelUID(uid))
        if channel is None:
            raise NotInitialisedException("Channel {} not found".format(uid))
        return channel

    @staticmethod
    def getItemState(item_name, default = None):
        if isinstance(item_name, str):
            state = scope.items.get(item_name)
            if state is None:
                raise NotInitialisedException("Item state for {} not found".format(item_name))
            if default is not None and java.instanceof(state, Java_UnDefType):
                state = default
            return state
        raise Exception("Unsupported parameter type {}".format(type(item_name)))

    @staticmethod
    def getItem(item_name):
        if isinstance(item_name, str):
            try:
                return scope.itemRegistry.getItem(item_name)
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
        scope.itemRegistry.add(item)
        return Registry.getItem(item_config['name'])

    @staticmethod
    def _createItem(item_config):
        if 'name' not in item_config or 'type' not in item_config:
            raise Exception('item_config.name or item_config.type not set')

        item_config['name'] = Item.buildSafeName(item_config['name'])

        base_item = None
        if item_config['type'] == 'Group' and 'giBaseType' in item_config:
            base_item = ITEM_BUILDER_FACTORY.newItemBuilder(item_config['giBaseType'], item_config['name'] + '_baseItem').build()
        if item_config['type'] != 'Group':
            item_config['groupFunction'] = None

        if 'tags' not in item_config:
            item_config['tags'] = []
        item_config['tags'].append("_DYNAMIC_")

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
            return item
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
    cleanupTrackerRegistered = False

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
        if not Timer.cleanupTrackerRegistered:
            scope.lifecycleTracker.addDisposeHook(Timer._clean)
            Timer.cleanupTrackerRegistered = True
        Timer.activeTimer.append(self)
        super().start()

    def cancel(self):
        if not self.is_alive():
            return
        Timer.activeTimer.remove(self)
        super().cancel()
